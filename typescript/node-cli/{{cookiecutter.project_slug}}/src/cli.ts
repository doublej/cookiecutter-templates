#!/usr/bin/env node
import * as p from '@clack/prompts'
import chalk from 'chalk'
import { Command } from 'commander'
import ora from 'ora'
import { LOCALES, localeFromEnv, normalize, t } from './i18n.js'
import { greet, name, version } from './index.js'

// Descriptions are declared before parsing, so an explicit --lang is read from argv up front.
const flag = process.argv.find(
  (arg, i, argv) => argv[i - 1] === '--lang' || arg.startsWith('--lang='),
)
const locale = normalize(flag?.replace('--lang=', '')) ?? localeFromEnv()

const program = new Command()
  .name(name)
  .version(version, '-V, --version', t(locale, 'options.version'))
  .helpOption('-h, --help', t(locale, 'options.help'))
  .helpCommand('help [command]', t(locale, 'commands.help'))
  .description(t(locale, 'description'))
  .option('--lang <locale>', t(locale, 'options.lang', { locales: LOCALES.join(', ') }))

async function askName(): Promise<string> {
  const answer = await p.text({
    message: t(locale, 'hello.prompt'),
    placeholder: t(locale, 'hello.defaultName'),
    defaultValue: t(locale, 'hello.defaultName'),
  })

  if (p.isCancel(answer)) {
    p.cancel(t(locale, 'hello.cancelled'))
    process.exit(0)
  }
  return answer
}

program
  .command('hello')
  .description(t(locale, 'hello.description'))
  .argument('[names...]', t(locale, 'hello.names'))
  .action(async (names: string[]) => {
    const targets = names.length > 0 ? names : [await askName()]

    const spinner = ora(t(locale, 'hello.working')).start()
    await new Promise((r) => setTimeout(r, 500))
    spinner.succeed(t(locale, 'hello.done', { count: targets.length }))

    for (const target of targets) console.log(chalk.green(greet(target, locale)))
  })

program.parse()
