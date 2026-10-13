// Each workspace keeps one theme colour: its position in the API list (ordered by id) cycles through the accents.
// Stable across reloads and never repeats among neighbours, which a random pick or an id hash cannot promise.
const TONES = ['yellow', 'blue', 'pink', 'olive']

export const workspaceTone = (workspaces, workspace) => TONES[workspaces.indexOf(workspace) % TONES.length]
