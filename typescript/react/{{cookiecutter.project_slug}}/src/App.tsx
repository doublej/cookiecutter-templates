import LanguageSwitcher from './LanguageSwitcher'
import { m } from './paraglide/messages'

export default function App() {
  return (
    <div>
      <LanguageSwitcher />
      <h1>{{ cookiecutter.project_name }}</h1>
      <p>{m.intro()}</p>
      <p>{m.greeting({ name: 'JJ' })}</p>
    </div>
  )
}
