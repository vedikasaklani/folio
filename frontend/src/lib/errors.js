// DRF returns { field: [messages] }; non_field_errors, `detail` and network failures go to `form`.
export function fieldErrors(err) {
  if (!err.status) return { form: "Can't reach the server. Check that the API is running." }
  const errors = {}
  for (const [key, msgs] of Object.entries(err.data ?? {})) {
    errors[key === 'non_field_errors' || key === 'detail' ? 'form' : key] = [msgs].flat().join(' ')
  }
  return Object.keys(errors).length ? errors : { form: 'Something went wrong. Try again.' }
}
