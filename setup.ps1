<#
    setup.ps1 - build or repair the AI video restoration environment.
    Safe to re-run: it resumes instead of starting over.

    WHY $ErrorActionPreference IS *NOT* "Stop" HERE
    -----------------------------------------------
    This script probes for things that are *expected* to fail - "is torch
    installed yet?", "is basicsr present so I can remove it?". Those probes
    write to stderr. When a native command's stderr is merged with 2>&1,
    PowerShell wraps each line in an ErrorRecord, and under
    $ErrorActionPreference = "Stop" that becomes a TERMINATING
    NativeCommandError. The earlier version of this script died on line 86 -
    the very check for whether PyTorch needed installing - and so could never
    reach the download. Native exit codes are checked explicitly instead.

    WHY THESE VERSIONS
    ------------------
    An RTX 5070 is Blackwell, compute capability sm_120. cu121 wheels carry
    kernels only up to sm_90, so torch.cuda.is_available() returns True while
    every kernel launch fails. sm_120 needs PyTorch >= 2.7 built for CUDA 12.8.

    basicsr is deliberately absent - it is the source of both the
    KeyError: '__version__' and torchvision.transforms.functional_tensor
    errors. Its only contribution was the RRDBNet class, which now lives in
    archs.py as plain PyTorch.
#>

$ErrorActionPreference = 'Continue'
$ProgressPreference    = 'SilentlyContinue'

$Root  = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Stamp = Join-Path $Root ".setup_ok"
$Py    = Join-Path $Root "venv\Scripts\python.exe"
$Step  = 0
$Total = 8

function Head($m) {
    $script:Step++
    Write-Host ""
    Write-Host "=== [$script:Step/$Total] $m" -ForegroundColor Cyan
}
function Ok($m)   { Write-Host "  [ok]   $m" }
function Note($m) { Write-Host "  ...    $m" }
function Warn($m) { Write-Host "  [warn] $m" -ForegroundColor Yellow }
function Die($m)  {
    Write-Host "  [FAIL] $m" -ForegroundColor Red
    Write-Host ""
    Write-Host "Setup did not finish. Nothing is wasted - run it again and it" -ForegroundColor Red
    Write-Host "resumes from this point." -ForegroundColor Red
    exit 1
}

# Run a native command without letting its stderr become a terminating error.
# Returns the exit code; echoes output when -Show is given.
function Native {
    param([string]$Exe, [string[]]$Arg, [switch]$Show)
    $script:LastOut = ""
    # If the executable does not exist, PowerShell raises CommandNotFound and
    # LEAVES $LASTEXITCODE AT ITS PREVIOUS VALUE - which can be 0, making a
    # missing interpreter look like a successful run. Check first.
    if (-not (Test-Path -LiteralPath $Exe) -and
        -not (Get-Command $Exe -ErrorAction SilentlyContinue)) {
        return 9009
    }
    $global:LASTEXITCODE = 0
    $lines = & $Exe @Arg 2>&1 | ForEach-Object { "$_" }
    $code  = $LASTEXITCODE
    if ($Show) { $lines | ForEach-Object { Write-Host "    $_" } }
    $script:LastOut = ($lines -join "`n")
    return $code
}

# A half-finished run must never look finished.
if (Test-Path $Stamp) { Remove-Item $Stamp -Force -ErrorAction SilentlyContinue }
Set-Location $Root

Write-Host ""
Write-Host "  AI Video Restoration - environment setup" -ForegroundColor White
Write-Host "  Project folder: $Root"

# --------------------------------------------------------------- 1. python
Head "Locating Python 3.11"
$pyExe = $null; $pyArgs = @()
foreach ($c in @(
        @{ Exe = "py";         Args = @("-3.11") },
        @{ Exe = "python3.11"; Args = @() },
        @{ Exe = "python";     Args = @() })) {
    $code = Native $c.Exe ($c.Args + @("--version"))
    if ($code -eq 0 -and $script:LastOut -match "3\.1[12]\.") {
        $pyExe = $c.Exe; $pyArgs = $c.Args
        Ok ($script:LastOut.Trim())
        break
    }
}
if (-not $pyExe) {
    Die "Python 3.11 not found. Install it:  winget install Python.Python.3.11"
}

# --------------------------------------------------------------- 2. folders
Head "Folders"
foreach ($d in @("models\SCUNet", "models\RealESRGAN")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null
}
Ok "models\SCUNet, models\RealESRGAN"

# --------------------------------------------------------------- 3. venv
Head "Virtual environment"
$venvOk = $false
if (Test-Path $Py) { $venvOk = ((Native $Py @("-c", "import sys")) -eq 0) }
if ($venvOk) {
    Ok "reusing the existing venv"
} else {
    if (Test-Path (Join-Path $Root "venv")) {
        Note "existing venv is broken - rebuilding"
        Remove-Item -Recurse -Force (Join-Path $Root "venv") -ErrorAction SilentlyContinue
    }
    if ((Native $pyExe ($pyArgs + @("-m", "venv", (Join-Path $Root "venv"))) -Show) -ne 0) {
        Die "could not create the virtual environment"
    }
    Ok "created"
}
Note "updating pip, setuptools and wheel"
Native $Py @("-m", "pip", "install", "--upgrade", "--quiet",
             "pip", "setuptools", "wheel") | Out-Null
Ok "package tools up to date"

# --------------------------------------------------------------- 4. pytorch
Head "PyTorch with sm_120 (Blackwell) kernels"
$haveTorch = $false
if ((Native $Py @("-c", "import torch")) -eq 0) {
    Native $Py @("-c", "import torch;print(torch.__version__)") | Out-Null
    $tv = $script:LastOut.Trim()
    Native $Py @("-c", "import torch;print(' '.join(torch.cuda.get_arch_list()))") | Out-Null
    if ($script:LastOut -match "sm_120") {
        Ok "already installed: torch $tv, has sm_120"
        $haveTorch = $true
    } else {
        Note "torch $tv has no sm_120 kernels - replacing it"
        Native $Py @("-m", "pip", "uninstall", "-y", "torch", "torchvision") | Out-Null
    }
}

if (-not $haveTorch) {
    Note "downloading about 2.5 GB - this is the slow part, please wait"
    Note "there is no progress bar; the next message appears when it lands"
    $installed = $false
    foreach ($idx in @("cu128", "cu129")) {
        Note "trying the $idx wheel index"
        $code = Native $Py @("-m", "pip", "install", "--upgrade",
                             "--progress-bar", "off",
                             "--retries", "10", "--timeout", "120",
                             "torch", "torchvision",
                             "--index-url", "https://download.pytorch.org/whl/$idx") -Show
        if ($code -eq 0 -and (Native $Py @("-c", "import torch")) -eq 0) { $installed = $true; break }
        Warn "$idx did not work"
    }
    if (-not $installed) {
        Die "PyTorch did not install. Check your internet connection and run again."
    }
    Ok "installed"
}

# --------------------------------------------------------------- 5. deps
Head "Remaining dependencies"
$code = Native $Py @("-m", "pip", "install", "--upgrade", "--progress-bar", "off",
                     "numpy", "einops", "tqdm", "requests") -Show
if ($code -ne 0) { Die "could not install numpy / einops / tqdm / requests" }
Ok "numpy, einops, tqdm, requests"

Native $Py @("-m", "pip", "uninstall", "-y",
             "basicsr", "realesrgan", "gfpgan", "facexlib") | Out-Null
Ok "basicsr and friends confirmed absent"

# --------------------------------------------------------------- 6. models
Head "Model weights"
$models = @(
    @{ Path = "models\RealESRGAN\RealESRGAN_x4plus.pth"
       Url  = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
       Min  = 60MB; Note = "4x upscaler, 67 MB" },
    @{ Path = "models\RealESRGAN\realesr-general-x4v3.pth"
       Url  = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"
       Min  = 3MB;  Note = "fast preview model, 5 MB" },
    @{ Path = "models\SCUNet\scunet_color_real_psnr.pth"
       Url  = "https://github.com/cszn/KAIR/releases/download/v1.0/scunet_color_real_psnr.pth"
       Min  = 60MB; Note = "denoiser, 69 MB" }
)
foreach ($m in $models) {
    $dest = Join-Path $Root $m.Path
    $name = Split-Path $m.Path -Leaf
    if ((Test-Path $dest) -and ((Get-Item $dest).Length -ge $m.Min)) {
        Ok "$name already present"
        continue
    }
    if (Test-Path $dest) {
        Note "$name is truncated - fetching again"
        Remove-Item $dest -Force -ErrorAction SilentlyContinue
    }
    Note "downloading $name  ($($m.Note))"
    try {
        Invoke-WebRequest -Uri $m.Url -OutFile $dest -UseBasicParsing -ErrorAction Stop
    } catch {
        Die "could not download $name - $($_.Exception.Message)"
    }
    if (-not (Test-Path $dest) -or (Get-Item $dest).Length -lt $m.Min) {
        Die "$name downloaded but is too small to be valid"
    }
    Ok "$name"
}

# --------------------------------------------------------------- 7. ffmpeg
Head "ffmpeg"
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Die "ffmpeg is not on PATH. Install it and open a NEW window: winget install Gyan.FFmpeg"
}
Ok "found on PATH"
Native ffmpeg @("-hide_banner", "-encoders") | Out-Null
if ($script:LastOut -match "hevc_nvenc") { Ok "hevc_nvenc available" }
else { Warn "hevc_nvenc missing - encoding will fall back to the CPU and be slow" }

# --------------------------------------------------------------- 8. verify
Head "Verifying it all actually works"
$code = Native $Py @((Join-Path $Root "verify_setup.py")) -Show
if ($code -ne 0) { Die "verification failed - see the messages above" }

"setup completed $(Get-Date -Format s)" | Set-Content $Stamp
Write-Host ""
Write-Host "  Setup complete." -ForegroundColor Green
exit 0
