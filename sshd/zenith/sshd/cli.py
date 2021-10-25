import logging
import os
import pathlib
import subprocess

import click

from .config import SSHDConfig
from .tunnel import run as run_tunnel


@click.group()
@click.option("--config", type = click.Path(exists = True), help = "Path to configuration file")
@click.pass_context
def main(ctx, config):
    """
    Zenith SSHD utilities.
    """
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = SSHDConfig(_path = config)
    ctx.obj["CONFIG"].logging.apply()
    ctx.obj["LOGGER"] = logging.getLogger(__name__)


@main.command()
@click.argument("key_type")
@click.argument("key_content")
def authorized_keys(key_type, key_content):
    """
    Authorized keys command for Zenith SSHD instances.
    """
    # For now, all keys are accepted
    click.echo(f"{key_type} {key_content}")


# The hostkeys to create, along with the number of bytes
HOSTKEYS = [
    ("dsa",     None),
    ("rsa",     4096),
    ("ecdsa",   521),
    ("ed25519", None)
]


@main.command()
@click.pass_context
def ensure_hostkeys(ctx):
    """
    Ensure that the required SSHD hostkeys exist.
    """
    ctx.obj["LOGGER"].info("Ensuring host keys exist")
    # Generate unique hostkeys in the SSHD run directory if not present
    run_directory = pathlib.Path(ctx.obj["CONFIG"].run_directory)
    for key_type, key_bits in HOSTKEYS:
        key_file = run_directory / f"ssh_host_{key_type}_key"
        if not key_file.exists():
            ctx.obj["LOGGER"].info(f"Generating {key_type} host key at {key_file}")
            keygen_args = ["ssh-keygen", "-q", "-N", "", "-t", key_type, "-f", str(key_file)]
            if key_bits:
                keygen_args.extend(["-b", str(key_bits)])
            subprocess.check_call(keygen_args)


@main.command()
@click.pass_context
def start(ctx):
    """
    Configure and start a Zenith SSHD server.
    """
    # Ensure the hostkeys are present
    ctx.forward(ensure_hostkeys)
    ctx.obj["LOGGER"].info("Collecting forwarded environment variables")
    # Ensure all environment variables starting ZENITH_SSHD are forwarded by SSHD
    forward_env = " ".join(
        f"{name}=\"{value}\""
        for name, value in os.environ.items()
        if name.startswith("ZENITH_SSHD_")
    )
    ctx.obj["LOGGER"].info("Starting SSHD")
    # Run SSHD by replacing the current process
    sshd_executable = ctx.obj["CONFIG"].sshd_executable
    os.execl(sshd_executable, sshd_executable, "-D", "-e", "-o", f"SetEnv={forward_env}")


@main.command()
@click.pass_context
def tunnel(ctx):
    """
    Configures a Zenith tunnel for a connecting client.
    """
    run_tunnel(ctx.obj["CONFIG"])
