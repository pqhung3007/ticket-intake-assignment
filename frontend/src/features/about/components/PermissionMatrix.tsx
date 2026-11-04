import { Check, Minus } from 'lucide-react'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

type Cell = boolean | string
const ROWS: { action: string; member: Cell; reporter: Cell; triager: Cell; agent: Cell }[] = [
  { action: 'See tickets', member: 'non-confidential', reporter: true, triager: true, agent: 'as the user' },
  { action: 'See confidential tickets', member: false, reporter: 'own', triager: true, agent: 'as the user' },
  { action: 'File a ticket', member: true, reporter: true, triager: true, agent: true },
  { action: 'Edit content', member: false, reporter: 'while active', triager: true, agent: false },
  { action: 'Close / reopen', member: false, reporter: true, triager: true, agent: false },
  { action: 'Start / resolve', member: false, reporter: false, triager: true, agent: false },
  { action: 'Assign', member: false, reporter: false, triager: true, agent: false },
  { action: 'Comment', member: true, reporter: true, triager: true, agent: false },
  { action: 'Grant triager role', member: false, reporter: false, triager: 'admins only', agent: false },
]

function Value({ v }: { v: Cell }) {
  if (v === true) return <Check className="text-st-resolved size-4" aria-label="yes" />
  if (v === false) return <Minus className="text-muted-foreground size-4" aria-label="no" />
  return <span className="text-muted-foreground text-xs">{v}</span>
}

export function PermissionMatrix() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Action</TableHead>
          <TableHead>Member</TableHead>
          <TableHead>Reporter</TableHead>
          <TableHead>Triager</TableHead>
          <TableHead>Agent</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {ROWS.map((r) => (
          <TableRow key={r.action}>
            <TableCell className="font-medium">{r.action}</TableCell>
            {([r.member, r.reporter, r.triager, r.agent] as Cell[]).map((v, i) => (
              <TableCell key={i} className="whitespace-normal">
                <Value v={v} />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
