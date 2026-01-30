#!/usr/bin/env node
import { Command } from 'commander'
import * as p from '@clack/prompts'
import chalk from 'chalk'
import ora from 'ora'
import { name, version, greet } from './index.js'

const program = new Command()
  .name(name)
  .version(version)
  .description('{{ cookiecutter.description }}')

program
  .command('hello')
  .description('Say hello')
  .argument('[name]', 'Name to greet')
  .action(async (nameArg?: string) => {
    let target = nameArg

    if (!target) {
      target = (await p.text({
        message: 'What is your name?',
        placeholder: 'World',
        defaultValue: 'World',
      })) as string

      if (p.isCancel(target)) {
        p.cancel('Cancelled')
        process.exit(0)
      }
    }

    const spinner = ora('Processing...').start()
    await new Promise((r) => setTimeout(r, 500))
    spinner.succeed('Done!')

    console.log(chalk.green(greet(target)))
  })

program.parse()
