/**
 * Account tree component for chart of accounts (Epic 26).
 */

import { useState } from "react";
import { ChevronRight, Circle, Folder, FolderOpen, MoreHorizontal } from "lucide-react";

import type { Account, AccountTreeNode } from "@/domain/accounting/types";
import { ROOT_TYPE_COLORS } from "@/domain/accounting/types";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface AccountTreeProps {
  tree: AccountTreeNode[];
  onSelect?: (account: Account) => void;
  onEdit?: (account: Account) => void;
  onFreeze?: (account: Account) => void;
  onUnfreeze?: (account: Account) => void;
  onDisable?: (account: Account) => void;
  onDelete?: (account: Account) => void;
  selectedId?: string | null;
  showDisabled?: boolean;
}

export function AccountTree({
  tree,
  onSelect,
  onEdit,
  onFreeze,
  onUnfreeze,
  onDisable,
  onDelete,
  selectedId,
  showDisabled = false,
}: AccountTreeProps) {
  return (
    <div className="space-y-1">
      {tree.map((node) => (
        <AccountTreeNode
          key={node.id}
          node={node}
          level={0}
          onSelect={onSelect}
          onEdit={onEdit}
          onFreeze={onFreeze}
          onUnfreeze={onUnfreeze}
          onDisable={onDisable}
          onDelete={onDelete}
          selectedId={selectedId}
          showDisabled={showDisabled}
        />
      ))}
    </div>
  );
}

interface AccountTreeNodeProps {
  node: AccountTreeNode;
  level: number;
  onSelect?: (account: Account) => void;
  onEdit?: (account: Account) => void;
  onFreeze?: (account: Account) => void;
  onUnfreeze?: (account: Account) => void;
  onDisable?: (account: Account) => void;
  onDelete?: (account: Account) => void;
  selectedId?: string | null;
  showDisabled?: boolean;
}

function AccountTreeNode({
  node,
  level,
  onSelect,
  onEdit,
  onFreeze,
  onUnfreeze,
  onDisable,
  onDelete,
  selectedId,
  showDisabled,
}: AccountTreeNodeProps) {
  const [isOpen, setIsOpen] = useState(level < 1);

  const hasChildren = node.children.length > 0;
  const isSelected = selectedId === node.id;
  const rootColor = ROOT_TYPE_COLORS[node.root_type];

  // Filter out disabled nodes if not showing them
  const visibleChildren = showDisabled
    ? node.children
    : node.children.filter((child) => !child.is_disabled);

  if (node.is_disabled && !showDisabled) {
    return null;
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div
        className={`
          flex items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors
          ${isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted/50"}
          ${node.is_disabled ? "opacity-50" : ""}
        `}
        style={{ paddingLeft: `${level * 1.5 + 0.5}rem` }}
      >
        {/* Expand/Collapse button */}
        {hasChildren ? (
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 shrink-0"
              onClick={() => setIsOpen(!isOpen)}
            >
              <ChevronRight
                className={`h-4 w-4 transition-transform ${isOpen ? "rotate-90" : ""}`}
              />
            </Button>
          </CollapsibleTrigger>
        ) : (
          <span className="h-5 w-5 shrink-0" />
        )}

        {/* Account type icon */}
        <span
          className="shrink-0 text-xs font-semibold"
          style={{ color: rootColor }}
        >
          {node.is_group ? (
            <Folder className="h-4 w-4" />
          ) : (
            <Circle className="h-3 w-3 fill-current" />
          )}
        </span>

        {/* Account info */}
        <button
          className="flex flex-1 items-center gap-2 text-left"
          onClick={() => onSelect?.(node)}
        >
          <span className="font-mono text-xs text-muted-foreground">
            {node.account_number}
          </span>
          <span className="truncate">{node.account_name}</span>
          {node.is_frozen && (
            <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
              Frozen
            </span>
          )}
          {node.is_disabled && (
            <span className="shrink-0 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-800">
              Disabled
            </span>
          )}
        </button>

        {/* Actions menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {onEdit && (
              <DropdownMenuItem onClick={() => onEdit(node)}>
                Edit
              </DropdownMenuItem>
            )}
            {!node.is_group && onFreeze && !node.is_frozen && (
              <DropdownMenuItem onClick={() => onFreeze(node)}>
                Freeze
              </DropdownMenuItem>
            )}
            {!node.is_group && onUnfreeze && node.is_frozen && (
              <DropdownMenuItem onClick={() => onUnfreeze(node)}>
                Unfreeze
              </DropdownMenuItem>
            )}
            {!node.is_group && onDisable && !node.is_disabled && (
              <DropdownMenuItem onClick={() => onDisable(node)}>
                Disable
              </DropdownMenuItem>
            )}
            {(onFreeze || onDisable) && (node.is_frozen || node.is_disabled) && (
              <DropdownMenuSeparator />
            )}
            {onDelete && visibleChildren.length === 0 && (
              <DropdownMenuItem
                onClick={() => onDelete(node)}
                className="text-destructive"
              >
                Delete
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Children */}
      {hasChildren && (
        <CollapsibleContent>
          {visibleChildren.map((child) => (
            <AccountTreeNode
              key={child.id}
              node={child}
              level={level + 1}
              onSelect={onSelect}
              onEdit={onEdit}
              onFreeze={onFreeze}
              onUnfreeze={onUnfreeze}
              onDisable={onDisable}
              onDelete={onDelete}
              selectedId={selectedId}
              showDisabled={showDisabled}
            />
          ))}
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}

interface AccountBadgeProps {
  account: Account;
  showType?: boolean;
}

export function AccountBadge({ account, showType = true }: AccountBadgeProps) {
  const rootColor = ROOT_TYPE_COLORS[account.root_type];

  return (
    <div className="flex items-center gap-1.5">
      <span
        className="shrink-0 text-xs font-semibold"
        style={{ color: rootColor }}
      >
        {account.is_group ? (
          <Folder className="h-4 w-4" />
        ) : (
          <FolderOpen className="h-4 w-4" />
        )}
      </span>
      <span className="font-mono text-xs text-muted-foreground">
        {account.account_number}
      </span>
      <span className="truncate text-sm">{account.account_name}</span>
      {showType && (
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-xs font-medium"
          style={{
            backgroundColor: `${rootColor}20`,
            color: rootColor,
          }}
        >
          {account.account_type}
        </span>
      )}
    </div>
  );
}
