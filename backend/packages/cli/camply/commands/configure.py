"""
Configuration management command for local settings and notification tokens.
"""

import click

from camply.config import CamplySettings, load_settings, save_settings
from camply.output import print_banner, print_info

_KEY_PREFIX_LENGTH: int = 4
# Length of key prefix to display when masking tokens.


@click.command(name="configure")
@click.option(
    "--pushover-user-key",
    default=None,
    help="Pushover User Key for push notification delivery.",
)
@click.option(
    "--pushover-app-token",
    default=None,
    help="Pushover Application API Token.",
)
@click.option(
    "--show",
    is_flag=True,
    default=False,
    help="Display currently configured settings without modifying them.",
)
def configure_command(
    pushover_user_key: str | None,
    pushover_app_token: str | None,
    show: bool,
) -> None:
    """
    Configure local settings and credentials for notifications.
    """
    settings = load_settings()

    if show:
        user_key_display = (
            f"{settings.pushover_user_key[:_KEY_PREFIX_LENGTH]}..."
            if settings.pushover_user_key
            and len(settings.pushover_user_key) >= _KEY_PREFIX_LENGTH
            else "(Not configured)"
        )
        app_token_display = (
            f"{settings.pushover_app_token[:_KEY_PREFIX_LENGTH]}..."
            if settings.pushover_app_token
            and len(settings.pushover_app_token) >= _KEY_PREFIX_LENGTH
            else "(Not configured)"
        )
        message = (
            f"[bold]Pushover User Key:[/bold] {user_key_display}\n"
            f"[bold]Pushover App Token:[/bold] {app_token_display}\n"
            f"[bold]Default Provider:[/bold] {settings.default_provider}"
        )
        print_banner(title="Current Configuration", message=message, style="bold cyan")
        return

    # If neither provided on CLI, prompt interactively
    if not pushover_user_key and not pushover_app_token:
        pushover_user_key = click.prompt(
            "Enter Pushover User Key",
            default=settings.pushover_user_key or "",
            show_default=True,
        )
        pushover_app_token = click.prompt(
            "Enter Pushover Application Token",
            default=settings.pushover_app_token or "",
            show_default=True,
        )

    updated_settings = CamplySettings(
        pushover_user_key=pushover_user_key or settings.pushover_user_key,
        pushover_app_token=pushover_app_token or settings.pushover_app_token,
        default_provider=settings.default_provider,
    )
    saved_path = save_settings(updated_settings)
    print_info(f"Configuration successfully saved to [bold]{saved_path}[/bold]")
