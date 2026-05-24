use anyhow::Result;
use clap::Parser;

#[derive(Parser)]
#[command(name = "{{ cookiecutter.project_slug }}")]
#[command(about = "{{ cookiecutter.description }}")]
struct Cli {
    /// Input to process
    input: Option<String>,

    /// Enable verbose output
    #[arg(short, long)]
    verbose: bool,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    if let Some(input) = &cli.input {
        println!("Processing: {input}");
    } else {
        println!("No input provided. Use --help for usage.");
    }

    Ok(())
}
