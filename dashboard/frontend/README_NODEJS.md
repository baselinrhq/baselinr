# Node.js PATH Fix for Windows

If you get `npm is not recognized` after installing Node.js, follow these steps:

## Quick Fix (Temporary)

Run this in your PowerShell terminal:

```powershell
$env:PATH += ";C:\Program Files\nodejs"
node --version
npm --version
```

This fixes it for the current session only.

## Permanent Fix

### Option 1: Restart Terminal/IDE (Recommended)
The Node.js installer should have already added it to your system PATH. Simply:
1. **Close and restart** your PowerShell terminal
2. **Or restart Cursor/VS Code** if you're using it
3. The PATH should now include Node.js automatically

### Option 2: Run Helper Script
```powershell
cd dashboard/frontend
.\fix-nodejs-path.ps1
```

### Option 3: Manually Add to System PATH
1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "System variables", find "Path" and click "Edit"
5. Click "New" and add: `C:\Program Files\nodejs`
6. Click "OK" on all dialogs
7. **Restart your terminal**

## Verify Installation

After fixing, verify it works:

```powershell
node --version   # Should show: v24.x.x or similar
npm --version    # Should show: 11.x.x or similar
```

## Common Node.js Installation Paths

- `C:\Program Files\nodejs\` (64-bit, default)
- `C:\Program Files (x86)\nodejs\` (32-bit)
- `%LOCALAPPDATA%\Programs\nodejs\` (User installation)

## Still Not Working?

1. **Reinstall Node.js** from [nodejs.org](https://nodejs.org/)
   - Make sure to check "Add to PATH" during installation
   - Choose "Add to PATH for all users" if available

2. **Check if Node.js is actually installed:**
   ```powershell
   Test-Path "C:\Program Files\nodejs\node.exe"
   ```

3. **Find where Node.js is installed:**
   ```powershell
   Get-ChildItem "C:\Program Files" -Filter "nodejs" -Recurse -ErrorAction SilentlyContinue
   ```

## Next Steps

Once Node.js and npm are working:

```powershell
cd dashboard/frontend
npm install
npm run dev
```


