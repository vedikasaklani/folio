import { useReducer, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import IconButton from '../components/ui/IconButton'
import { cx } from '../components/ui/cx'
import { FileText, LayoutGrid, LogOut, PanelLeftClose, PanelLeftOpen } from '../components/ui/icons'
import PageEditor from '../components/PageEditor'
import PageTree from '../components/PageTree'
import { initialTree, treeReducer } from '../lib/pageTree'
import { canWrite, ROLE_LABEL } from '../lib/roles'
import './WorkspaceView.css'

const SIDEBAR_KEY = 'folio_sidebar' // '1' = collapsed

// Mount with key={workspace.id} so switching workspaces resets the tree and selection.
export default function WorkspaceView({ workspace, tone, onSwitch, onSignOut }) {
  const [tree, dispatch] = useReducer(treeReducer, initialTree)
  const [selectedId, setSelectedId] = useState(null)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_KEY) === '1')
  const writable = canWrite(workspace.role)
  const selected = tree.pages[selectedId] // gone once the page (or an ancestor) is deleted

  function toggleSidebar() {
    localStorage.setItem(SIDEBAR_KEY, collapsed ? '0' : '1')
    setCollapsed(!collapsed)
  }

  return (
    <div className={cx('view', collapsed && 'is-collapsed')}>
      <div className="view__side">
        <aside id="sidebar" className="view__panel" aria-label="Workspace">
          <header className="view__head">
            <h1 className="t-heading">{workspace.name}</h1>
            <Badge tone={tone}>{ROLE_LABEL[workspace.role]}</Badge>
          </header>
          <div className="view__tree">
            <PageTree
              workspaceId={workspace.id}
              tree={tree}
              dispatch={dispatch}
              selectedId={selectedId}
              onSelect={setSelectedId}
              canWrite={writable}
              collapsed={collapsed}
            />
          </div>
          <footer className="view__foot">
            {collapsed ? (
              <IconButton icon={LogOut} label="Sign out" onClick={onSignOut} />
            ) : (
              <Button variant="ghost" size="xs" icon={LogOut} onClick={onSignOut}>
                Sign out
              </Button>
            )}
          </footer>
        </aside>
        <div className="view__edge" role="group" aria-label="Sidebar controls">
          <IconButton
            variant="raised"
            size="md"
            icon={collapsed ? PanelLeftOpen : PanelLeftClose}
            label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
            aria-controls="sidebar"
            onClick={toggleSidebar}
          />
          <IconButton variant="raised" size="md" icon={LayoutGrid} label="Switch workspace" onClick={onSwitch} />
        </div>
      </div>
      <main className="view__main">
        {selected ? (
          <PageEditor
            key={selectedId}
            pageId={selectedId}
            canWrite={writable}
            onSaved={(page) => dispatch({ type: 'renamed', id: page.id, name: page.name })}
          />
        ) : (
          <div className="view__empty" role="status">
            <FileText aria-hidden="true" />
            <p className="t-body t-muted">Select a page{writable ? ' or create one' : ''} to get started.</p>
          </div>
        )}
      </main>
    </div>
  )
}
