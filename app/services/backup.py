"""Database backup service: pg_dump specific tables and upload via SFTP."""

import io
import logging
import os
import posixpath
import subprocess
import tempfile
import threading
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# All tables to include in backup — excludes voters and voters_backup_* tables
BACKUP_TABLES = [
    "users",
    "signatures",
    "books",
    "batches",
    "collectors",
    "organizations",
    "data_enterers",
    "paid_collectors",
    "settings",
    "voter_imports",
]


def is_configured() -> bool:
    """Return True if all required backup settings are present."""
    from app.models import Settings

    return all(
        Settings.get(k)
        for k in (
            "backup_scp_host",
            "backup_scp_user",
            "backup_scp_key_content",
            "backup_scp_remote_path",
        )
    )


def run_backup_async(app) -> None:
    """Kick off a backup in a background daemon thread.

    Sets status to 'running' synchronously before returning so the caller
    can immediately reflect that state in the UI.

    Raises ValueError if backup is not configured or already running.
    """
    from app.models import Settings

    if not is_configured():
        raise ValueError("Backup is not fully configured.")

    current_status = Settings.get("backup_last_status", "")
    if current_status == "running":
        raise ValueError("A backup is already in progress.")

    Settings.set("backup_last_status", "running")
    Settings.set("backup_last_run", datetime.now().isoformat())

    thread = threading.Thread(target=_backup_thread, args=(app,), daemon=True)
    thread.start()


def _backup_thread(app) -> None:
    """Background thread: dump the database and upload via SFTP."""
    with app.app_context():
        from app.models import Settings

        db_url = os.environ.get("DATABASE_URL") or app.config.get(
            "SQLALCHEMY_DATABASE_URI", ""
        )
        scp_config = {
            "host": Settings.get("backup_scp_host"),
            "port": int(Settings.get("backup_scp_port", "22") or "22"),
            "user": Settings.get("backup_scp_user"),
            "key_content": Settings.get("backup_scp_key_content"),
            "remote_path": Settings.get("backup_scp_remote_path"),
        }

        dump_file = None
        try:
            dump_file = _create_pg_dump(db_url)
            _sftp_upload(dump_file, scp_config)
            Settings.set("backup_last_status", "success")
        except Exception as exc:
            logger.exception("Backup failed")
            # Truncate long error messages to fit in the settings value column
            Settings.set("backup_last_status", f"error:{str(exc)[:300]}")
        finally:
            if dump_file and os.path.exists(dump_file):
                try:
                    os.unlink(dump_file)
                except OSError:
                    pass


def _create_pg_dump(db_url: str) -> str:
    """Run pg_dump for BACKUP_TABLES only and return the path to the dump file."""
    # SQLAlchemy may prefix the URL with the driver name (e.g. postgresql+psycopg2://)
    clean_url = db_url.replace("+psycopg2", "").replace("+pg8000", "")
    parsed = urlparse(clean_url)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fd, dump_path = tempfile.mkstemp(suffix=f"-petition-qc-{timestamp}.dump")
    os.close(fd)

    cmd = ["pg_dump", "--format=custom"]
    for table in BACKUP_TABLES:
        cmd.extend(["--table", table])
    if parsed.hostname:
        cmd.extend(["-h", parsed.hostname])
    if parsed.port:
        cmd.extend(["-p", str(parsed.port)])
    if parsed.username:
        cmd.extend(["-U", parsed.username])
    dbname = parsed.path.lstrip("/")
    cmd.append(dbname)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    with open(dump_path, "wb") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

    if result.returncode != 0:
        os.unlink(dump_path)
        raise RuntimeError(
            f"pg_dump exited with code {result.returncode}: "
            f"{result.stderr.decode().strip()}"
        )

    return dump_path


def _load_pkey(key_content: str):
    """Load a paramiko PKey from a PEM/OpenSSH string, trying all key types.

    Normalises line endings first so browser-uploaded files work regardless
    of whether they were saved with LF or CRLF.
    """
    import paramiko

    key_content = key_content.replace("\r\n", "\n").replace("\r", "\n")
    for key_class in (
        paramiko.RSAKey,
        paramiko.Ed25519Key,
        paramiko.ECDSAKey,
        paramiko.DSSKey,
    ):
        try:
            return key_class.from_private_key(io.StringIO(key_content))
        except (paramiko.SSHException, ValueError):
            continue
    raise ValueError(
        "Could not load the private key — unsupported format or corrupted file. "
        "Supported types: RSA, Ed25519, ECDSA, DSA."
    )


def _make_ssh_client(scp_config: dict, timeout: int):
    """Return a connected paramiko SSHClient using the stored private key.

    Lets paramiko negotiate the pubkey algorithm freely (tries rsa-sha2-512,
    rsa-sha2-256, then ssh-rsa in order) so it works with both modern and
    legacy SSH servers.
    """
    import paramiko

    pkey = _load_pkey(scp_config["key_content"])
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        scp_config["host"],
        port=scp_config["port"],
        username=scp_config["user"],
        pkey=pkey,
        look_for_keys=False,
        allow_agent=False,
        timeout=timeout,
    )
    return client


def test_sftp_connection(scp_config: dict, password: str | None = None) -> tuple[bool, str]:
    """Attempt an SSH connection and return (success, message).

    If *password* is supplied, only password auth is tried.

    Otherwise, key auth is attempted three ways to maximise diagnostic value:
      A) Auto  — let paramiko negotiate (rsa-sha2-512 → rsa-sha2-256 → ssh-rsa)
      B) SHA-2 — disable legacy ssh-rsa entirely
      C) SHA-1 — disable rsa-sha2 variants (legacy servers only)

    The first strategy that succeeds is reported.  If all three fail the
    combined error messages are returned so the caller can see exactly where
    negotiation is breaking down.
    """
    import paramiko

    host = scp_config["host"]

    if password:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                host,
                port=scp_config["port"],
                username=scp_config["user"],
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=8,
            )
            client.close()
            return True, f"Connected to {host} via password successfully."
        except Exception as exc:
            return False, f"Password auth failed: {exc}"

    try:
        pkey = _load_pkey(scp_config["key_content"])
    except ValueError as exc:
        return False, str(exc)

    strategies = [
        ("Auto (rsa-sha2-512/256/ssh-rsa)",    {}),
        ("SHA-2 only (rsa-sha2-512/256)",       {"disabled_algorithms": {"pubkeys": ["ssh-rsa"]}}),
        ("Legacy SHA-1 only (ssh-rsa)",         {"disabled_algorithms": {"pubkeys": ["rsa-sha2-512", "rsa-sha2-256"]}}),
    ]
    errors = []
    for label, extra_kwargs in strategies:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                host,
                port=scp_config["port"],
                username=scp_config["user"],
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
                timeout=8,
                **extra_kwargs,
            )
            client.close()
            return True, f"Connected to {host} successfully [{label}]."
        except Exception as exc:
            errors.append(f"{label}: {exc}")
        finally:
            client.close()

    return False, " | ".join(errors)


def run_backup_sync(app) -> None:
    """Run a full backup synchronously (for use by the scheduler)."""
    with app.app_context():
        from app.models import Settings

        if not is_configured():
            logger.warning("Scheduled backup skipped: not configured.")
            return
        if Settings.get("backup_last_status") == "running":
            logger.warning("Scheduled backup skipped: already running.")
            return
        Settings.set("backup_last_status", "running")
        Settings.set("backup_last_run", datetime.now().isoformat())

    _backup_thread(app)


def _sftp_upload(local_path: str, scp_config: dict) -> None:
    """Upload a file to the remote server via SFTP (SSH)."""
    client = _make_ssh_client(scp_config, timeout=30)
    try:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        remote_filename = f"petition-qc-backup-{timestamp}.dump"
        remote_dir = scp_config["remote_path"].rstrip("/")
        remote_path = posixpath.join(remote_dir, remote_filename)

        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
    finally:
        client.close()
