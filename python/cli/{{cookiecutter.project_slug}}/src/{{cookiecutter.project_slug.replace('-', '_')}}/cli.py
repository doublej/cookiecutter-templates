import click


@click.group()
def main():
    """{{ cookiecutter.description }}"""
    pass


@main.command()
def hello():
    """Say hello."""
    click.echo("Hello from {{ cookiecutter.project_name }}!")


if __name__ == "__main__":
    main()
