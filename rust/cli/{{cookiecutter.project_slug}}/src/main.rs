use anyhow::Result;
use clap::Parser;

mod i18n;

// ponytail: clap's own chrome (Usage/Options headings, -h/-V text, parse errors) stays English;
// localize it with `help_template` + `disable_help_flag` when a user needs it
#[derive(Parser)]
#[command(name = "{{ cookiecutter.project_slug }}")]
#[command(about = translate_help("cli.about"))]
struct Cli {
    #[arg(help = translate_help("cli.input"))]
    input: Option<String>,

    #[arg(short, long, help = translate_help("cli.verbose"))]
    verbose: bool,

    #[arg(long, global = true, help = translate_help("cli.lang"))]
    lang: Option<String>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let lang = cli
        .lang
        .as_deref()
        .map_or_else(i18n::locale_from_env, i18n::normalize);

    if let Some(input) = &cli.input {
        println!(
            "{}",
            i18n::t(lang, "output.processing", &[("input", input.as_str())])
        );
        if cli.verbose {
            let count = input.chars().count().to_string();
            println!(
                "{}",
                i18n::t(lang, "output.characters", &[("count", count.as_str())])
            );
        }
    } else {
        println!("{}", i18n::t(lang, "output.no_input", &[]));
    }

    Ok(())
}

/// Help comes from the env locale: clap builds it before `--lang` is parsed.
fn translate_help(key: &str) -> String {
    i18n::t(i18n::locale_from_env(), key, &[])
}
