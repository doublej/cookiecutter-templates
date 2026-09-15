import click

from {{ cookiecutter.project_slug.replace('-', '_') }}.i18n import LOCALES, locale_from_env, t


@click.group()
@click.option(
    "--lang",
    type=click.Choice(LOCALES),
    help="Output language; defaults to LC_ALL, LC_MESSAGES or LANG, then en.",
)
@click.pass_context
def main(ctx: click.Context, lang: str | None) -> None:
    """{{ cookiecutter.description }}"""
    ctx.obj = lang or locale_from_env()


@main.command()
@click.pass_obj
def hello(locale: str) -> None:
    """Say hello."""
    name = "{{ cookiecutter.project_name }}"
    click.echo(t("hello.greeting", locale, name=name))
    click.echo(t("hello.languages", locale, count=len(LOCALES)))


if __name__ == "__main__":
    main()
