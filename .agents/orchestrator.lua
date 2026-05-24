-- orchestrator.lua — Neovim integration for the orchestration harness
-- Source:  luafile .agents/orchestrator.lua
-- Lazy:   { dir = '.agents', file = 'orchestrator.lua' }
--
-- Commands:
--   :Orch feature/X --prompt "..."   scaffold
--   :Orch implement/X                 generate code
--   :Orch modify/X "...prompt..."     amend spec
--   :Orch bugfix/X "...prompt..."     document defect
--   :Orch delete/X                    purge feature + branch
--   :Orch last                        re-run the last command
--
-- The terminal buffer stays open so you see live output as files are written.
-- Neovim autoreads changed buffers when you focus them (<C-w>w, :e!).

local M = {}

local repo_root = vim.fn.getcwd()
local cmd_base = repo_root .. "/.agents/orchestrator.py"

-- Terminal window ID for the orchestrator output
local term_win = nil
local term_buf = nil
local last_cmd = nil

function M.run(args)
  local cmd = cmd_base .. " " .. args
  last_cmd = cmd
  local prev_win = vim.api.nvim_get_current_win()

  -- If terminal already exists and is valid, reuse it
  if term_buf and vim.api.nvim_buf_is_valid(term_buf) then
    local chan = vim.api.nvim_buf_get_var(term_buf, "terminal_job_id")
    vim.fn.chansend(chan, cmd .. "\n")
    -- Stay in the previous window, don't steal focus
    vim.api.nvim_set_current_win(prev_win)
    return
  end

  -- Open a new terminal in a horizontal split at the bottom
  vim.cmd("belowright split | terminal")
  term_buf = vim.api.nvim_get_current_buf()
  term_win = vim.api.nvim_get_current_win()

  -- Resize to ~10 lines
  vim.api.nvim_win_set_height(term_win, 10)

  -- Return focus to the previous window (user stays in their code buffer)
  vim.api.nvim_set_current_win(prev_win)

  -- Set up auto-cleanup on buffer delete
  vim.api.nvim_buf_attach(term_buf, false, {
    on_detach = function()
      term_win = nil
      term_buf = nil
    end,
  })

  -- Send the command once the shell is ready
  vim.fn.jobwait({}, 100)
  local chan = vim.api.nvim_buf_get_var(term_buf, "terminal_job_id")
  vim.fn.chansend(chan, cmd .. "\n")
end

function M.last()
  if last_cmd then
    M.run(last_cmd:gsub("^" .. cmd_base .. " ", ""))
  else
    print("[orchestrator] No previous command.")
  end
end

function M.toggle()
  if term_win and vim.api.nvim_win_is_valid(term_win) then
    vim.api.nvim_win_close(term_win, true)
    term_win = nil
    term_buf = nil
  end
end

-- User commands
vim.api.nvim_create_user_command("Orch", function(opts)
  M.run(opts.args)
end, { nargs = 1, desc = "Run orchestrator: feature/X, implement/X, modify/X, bugfix/X, delete/X" })

vim.api.nvim_create_user_command("OrchLast", function()
  M.last()
end, {})

vim.api.nvim_create_user_command("OrchToggle", function()
  M.toggle()
end, {})

-- Keymaps (normal mode)
vim.keymap.set("n", "<leader>or", "<cmd>OrchLast<CR>", { desc = "Re-run last orchestrator command" })
vim.keymap.set("n", "<leader>ot", "<cmd>OrchToggle<CR>", { desc = "Toggle orchestrator terminal" })
vim.keymap.set("n", "<leader>os", '<cmd>Orch feature/<CR>', { desc = "Scaffold new feature (type name + --prompt)" })
vim.keymap.set("n", "<leader>oi", '<cmd>Orch implement/<CR>', { desc = "Implement feature (type name)" })

print("[orchestrator] Loaded. Commands: :Orch, :OrchLast, :OrchToggle")
