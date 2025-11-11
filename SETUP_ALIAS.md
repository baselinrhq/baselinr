# Setting Up PowerShell Alias for Quick Activation

## Option 1: Simple Command (Recommended)

Just use the activation script:

```powershell
.\activate.ps1
```

## Option 2: Create PowerShell Alias (Permanent)

To create a permanent alias that works from anywhere:

### Step 1: Open Your PowerShell Profile

```powershell
# Open the profile in notepad
notepad $PROFILE

# If you get an error that the file doesn't exist, create it first:
New-Item -Path $PROFILE -Type File -Force
notepad $PROFILE
```

### Step 2: Add the Alias

Add this line to your profile:

```powershell
# ProfileMesh alias
function pm { Set-Location "C:\Users\benja\Documents\code_projects\profile_mesh"; .\activate.ps1 }
```

### Step 3: Reload Your Profile

```powershell
. $PROFILE
```

### Step 4: Use It!

Now from any directory, just type:

```powershell
pm
```

This will:
1. Navigate to your ProfileMesh directory
2. Activate the virtual environment
3. Show you helpful commands

## Option 3: Even Simpler - Just cd Alias

If you just want a quick way to get to the directory:

```powershell
# Add to $PROFILE
function pm { Set-Location "C:\Users\benja\Documents\code_projects\profile_mesh" }
```

Then use:
```powershell
pm
.\activate.ps1
```

## Option 4: Make Command

From within the ProfileMesh directory:

```powershell
make activate    # Shows activation instructions
make dev-setup   # Creates venv and installs everything
```

## Troubleshooting

If you get an execution policy error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

