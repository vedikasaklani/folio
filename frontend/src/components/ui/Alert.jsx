import { CircleAlert } from './icons'
import './Alert.css'

export default function Alert({ children }) {
  return (
    <div className="ui-alert" role="alert">
      <CircleAlert aria-hidden="true" />
      <p>{children}</p>
    </div>
  )
}
