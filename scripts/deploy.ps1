# ============================================================
#  ESP32-C3 MicroPython 一键部署脚本 (Windows PowerShell)
#  用法: .\deploy.ps1 [选项]
# ============================================================

param(
    [string]$Port = "",
    [string]$File = "app.py",
    [switch]$NoFix = $false,
    [int]$Monitor = 8,
    [int]$Retries = 2
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$MainFile = Join-Path $ProjectDir $File
$RemoteName = $File
$SerialPort = $Port
$RetryCount = 0
$ModuleFiles = @("config.py", "logger.py", "utils.py", "web_pages.py", "ble_service.py", "power_data.py", "wifi_manager.py")
$BootFile = Join-Path $ProjectDir "boot.py"

function Write-Step($msg) { Write-Host "`n==== $msg ====" -ForegroundColor Cyan }
function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ============================================================
#  ESP32-C3 串口智能扫描
#  通过 USB VID/PID 识别 Espressif 芯片
#  0x303A = Espressif USB, 0x10C4 = CP210x, 0x1A86 = CH340
# ============================================================

$ESP_VIDS = @(0x303A, 0x10C4, 0x1A86, 0x0403)

function Get-ChipHint {
    param([int]$Vid)
    switch ($Vid) {
        0x303A { return "ESP32-C3/S2/S3 (Espressif USB)" }
        0x10C4 { return "CP210x (Silicon Labs USB-UART)" }
        0x1A86 { return "CH340/CH341 (USB-UART)" }
        0x0403 { return "FTDI FT232 (USB-UART)" }
        default { return "Unknown USB device" }
    }
}

function Find-Esp32Port {
    Write-Step "步骤 1/7: 扫描 ESP32-C3 串口"

    Write-Info "当前系统: Windows"

    if ($SerialPort -ne "") {
        Write-Info "使用指定串口: $SerialPort"
        return
    }

    $espPorts = @()
    $otherPorts = @()

    $pyserialAvailable = $false
    try {
        python -c "from serial.tools import list_ports" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pyserialAvailable = $true
        }
    } catch {}

    if ($pyserialAvailable) {
        Write-Info "使用 pyserial 扫描串口设备..."
        Write-Host ""

        $portData = python -c @"
from serial.tools import list_ports
import sys
ports = list(list_ports.comports())
for p in sorted(ports, key=lambda x: x.device):
    vid = p.vid if p.vid else 0
    pid = p.pid if p.pid else 0
    print(f'{p.device}|{vid:#06x}|{pid:#06x}|{p.description}|{p.manufacturer or ""}|{p.hwid}')
"@ 2>$null

        if ($portData) {
            foreach ($line in $portData) {
                if ([string]::IsNullOrWhiteSpace($line)) { continue }
                $parts = $line -split '\|'
                $dev = $parts[0]
                $vidStr = $parts[1]
                $pidStr = $parts[2]
                $desc = $parts[3]
                $mfr = $parts[4]

                $vidInt = 0
                if ($vidStr -match '^0x([0-9a-fA-F]+)$') {
                    $vidInt = [Convert]::ToInt32($Matches[1], 16)
                }

                if ($ESP_VIDS -contains $vidInt) {
                    $chipHint = Get-ChipHint -Vid $vidInt
                    $espPorts += [PSCustomObject]@{
                        Device = $dev
                        Vid = $vidStr
                        Pid = $pidStr
                        ChipHint = $chipHint
                        Description = $desc
                        Manufacturer = $mfr
                    }
                    Write-Host "  [ESP32] $dev" -ForegroundColor Green
                    Write-Host "          VID=$vidStr PID=$pidStr | $chipHint"
                    Write-Host "          描述: $desc | 厂商: $(if($mfr){$mfr}else{'N/A'})"
                    Write-Host ""
                } else {
                    $otherPorts += [PSCustomObject]@{
                        Device = $dev
                        Vid = $vidStr
                        Pid = $pidStr
                        Description = $desc
                    }
                }
            }
        }
    } else {
        Write-Warn "pyserial 未安装，使用系统工具扫描..."
        Write-Host ""

        try {
            $comPorts = [System.IO.Ports.SerialPort]::GetPortNames()
            foreach ($com in $comPorts) {
                $espPorts += [PSCustomObject]@{
                    Device = $com
                    Vid = "N/A"
                    Pid = "N/A"
                    ChipHint = "可能为 ESP32 设备"
                    Description = $com
                    Manufacturer = ""
                }
                Write-Host "  [ESP32?] $com" -ForegroundColor Yellow
                Write-Host "           可能的 ESP32 设备（安装 pyserial 可精确识别）"
                Write-Host ""
            }
        } catch {
            Write-Err "无法扫描串口"
        }
    }

    Write-Host "------------------------------------------------------------"
    if ($espPorts.Count -eq 0) {
        Write-Err "未找到 ESP32-C3 设备"
        Write-Host ""
        Write-Host "  排查建议:"
        Write-Host "    1. 检查 USB 数据线是否连接（需支持数据传输，非仅充电线）"
        Write-Host "    2. 确认设备已上电（LED 指示灯亮起）"
        Write-Host "    3. Windows: 设备管理器 → 端口(COM和LPT) → 查看设备"
        Write-Host "    4. 安装 CP210x/CH340 驱动程序"
        Write-Host "    5. 安装 pyserial 获取更精确的扫描: pip install pyserial"
        exit 1
    } else {
        Write-Info "找到 $($espPorts.Count) 个 ESP32 设备"
        for ($i = 0; $i -lt $espPorts.Count; $i++) {
            Write-Host "    [$($i+1)] $($espPorts[$i].Device)"
        }
    }
    Write-Host "------------------------------------------------------------"

    if ($espPorts.Count -eq 1) {
        $SerialPort = $espPorts[0].Device
        Write-Info "自动选择串口: $SerialPort"
    } else {
        Write-Host ""
        Write-Warn "发现 $($espPorts.Count) 个 ESP32 设备，请选择:"
        for ($i = 0; $i -lt $espPorts.Count; $i++) {
            Write-Host "  [$($i+1)] $($espPorts[$i].Device) - $($espPorts[$i].ChipHint)"
        }
        Write-Host ""

        $choice = Read-Host "请输入序号 [1-$($espPorts.Count)]"
        if ($choice -match '^\d+$' -and [int]$choice -ge 1 -and [int]$choice -le $espPorts.Count) {
            $SerialPort = $espPorts[[int]$choice - 1].Device
            Write-Info "已选择串口: $SerialPort"
        } else {
            Write-Err "无效选择"
            exit 1
        }
    }
}

# ============================================================
#  步骤 2: 检查串口占用
# ============================================================
function Release-Port {
    Write-Step "步骤 2/7: 检查串口占用"
    Write-Info "串口占用检查（Windows 需手动关闭占用程序如 Thonny/PuTTY）"
    Write-Info "提示: 如串口被占用，请在设备管理器中查看或关闭相关程序"
}

# ============================================================
#  步骤 3: 验证连接
# ============================================================
function Verify-Connection {
    Write-Step "步骤 3/7: 验证设备连接"

    try {
        $result = python -m mpremote connect $SerialPort ls 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "设备连接成功"
            return
        }
    } catch {}

    Write-Warn "mpremote 无法连接（设备可能正在运行 BLE 程序）"
    Write-Info "尝试进入部署模式（创建 .deploy 标志文件后重启）..."

    python -c @"
import serial, time
try:
    s = serial.Serial('$SerialPort', 115200, timeout=2)
    time.sleep(0.1)
    s.write(b'\x03\x03')
    time.sleep(0.5)
    s.write(b'\x01')
    time.sleep(0.5)
    s.read(s.in_waiting or 4096)
    s.write(b'f=open(\".deploy\",\"w\");f.flush();f.close()\x04')
    time.sleep(0.5)
    s.read(s.in_waiting or 4096)
    s.write(b'\x02')
    time.sleep(0.3)
    s.read(s.in_waiting or 4096)
    s.write(b'\x04')
    time.sleep(3)
    s.read(s.in_waiting or 8192)
    s.dtr = False
    s.rts = False
    s.close()
    del s
except Exception:
    pass
"@ 2>$null

    Start-Sleep -Seconds 2

    $retries = 5
    for ($i = 1; $i -le $retries; $i++) {
        try {
            $result = python -m mpremote connect $SerialPort ls 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Info "设备连接成功（部署模式）"
                return
            }
        } catch {}
        Write-Warn "连接失败，第 $i/$retries 次重试..."
        Start-Sleep -Seconds 2
    }

    Write-Err "无法连接设备 ($SerialPort)，请检查："
    Write-Err "  1. USB 线是否连接（需支持数据传输，非仅充电线）"
    Write-Err "  2. 尝试物理重插 USB 后重新部署"
    exit 1
}

# ============================================================
#  步骤 3.5: 清理设备旧文件
# ============================================================
function Remove-LegacyFiles {
    Write-Step "步骤 3.5/7: 清理设备旧文件"
    foreach ($f in @("main.py")) {
        try {
            python -m mpremote connect $SerialPort rm :$f 2>$null
            Write-Info "已删除设备上的 $f"
        } catch {}
    }
    Write-Info "旧文件清理完成"
}

# ============================================================
#  步骤 4: BOM 检查与语法检查
# ============================================================
function Check-File {
    Write-Step "步骤 4/7: 文件检查"

    $allFiles = @($MainFile, $BootFile)
    foreach ($mod in $ModuleFiles) {
        $allFiles += Join-Path $ProjectDir $mod
    }

    foreach ($f in $allFiles) {
        if (-not (Test-Path $f)) {
            Write-Err "文件不存在: $f"
            exit 1
        }

        $bytes = [System.IO.File]::ReadAllBytes($f)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            Write-Warn "检测到 UTF-8 BOM ($f)，正在移除..."
            $newBytes = New-Object byte[] ($bytes.Length - 3)
            [Array]::Copy($bytes, 3, $newBytes, 0, $bytes.Length - 3)
            [System.IO.File]::WriteAllBytes($f, $newBytes)
            Write-Info "BOM 已移除: $f"
        }
    }

    Write-Info "BOM 检查通过 ($($allFiles.Count) 个文件)"

    try {
        python -c "import py_compile; py_compile.compile('$MainFile', doraise=True)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "语法检查通过"
        } else {
            Write-Err "语法检查失败！"
            python -c "import py_compile; py_compile.compile('$MainFile', doraise=True)"
            exit 1
        }
    } catch {
        Write-Err "语法检查失败！"
        exit 1
    }
}

# ============================================================
#  步骤 5: 上传文件
# ============================================================
function Upload-File {
    Write-Step "步骤 5/7: 上传文件"

    foreach ($mod in $ModuleFiles) {
        $src = Join-Path $ProjectDir $mod
        $localSize = (Get-Item $src).Length
        Write-Info "上传模块: $mod ($localSize bytes)"
        python -m mpremote connect $SerialPort cp $src ":$mod"
        if ($LASTEXITCODE -ne 0) {
            Write-Err "上传失败: $mod"
            exit 1
        }
    }

    $localSize = (Get-Item $MainFile).Length
    Write-Info "上传主程序: $RemoteName ($localSize bytes)"

    python -m mpremote connect $SerialPort cp $MainFile ":$RemoteName"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "上传主程序失败"
        exit 1
    }

    $localSize = (Get-Item $BootFile).Length
    Write-Info "上传启动入口: boot.py ($localSize bytes)"
    python -m mpremote connect $SerialPort cp $BootFile ":boot.py"
    if ($LASTEXITCODE -eq 0) {
        Write-Info "全部上传成功 ($($ModuleFiles.Count) 个模块 + app.py + boot.py)"
    } else {
        Write-Err "上传 boot.py 失败"
        exit 1
    }
}

# ============================================================
#  步骤 6: 启动运行
# ============================================================
function Run-Program {
    Write-Step "步骤 6/7: 启动程序"

    Write-Info "删除部署模式标志，重启设备..."
    python -m mpremote connect $SerialPort rm :.deploy 2>$null

    Write-Info "设备重启中..."
    Start-Sleep -Seconds 5

    Write-Info "🎉 部署成功！设备将自动运行 BLE 程序"
}

# ============================================================
#  步骤 7: 日志分析与自修复
# ============================================================
function Analyze-Log {
    param([string]$LogData)

    Write-Step "步骤 7/7: 日志分析"

    $hasError = $false
    $errorType = ""

    if ($LogData -match "蓝牙功率计已启动") { Write-Info "✅ 蓝牙启动正常" }
    if ($LogData -match "WiFi热点已启动")   { Write-Info "✅ WiFi 启动正常" }
    if ($LogData -match "Web服务器已启动")   { Write-Info "✅ Web 服务器启动正常" }

    if ($LogData -match "Traceback")  { $hasError = $true; $errorType = "Traceback";  Write-Err "❌ 检测到运行时异常" }
    if ($LogData -match "NameError")  { $hasError = $true; $errorType = "NameError";  Write-Err "❌ 检测到 NameError" }
    if ($LogData -match "ImportError"){ $hasError = $true; $errorType = "ImportError"; Write-Err "❌ 检测到 ImportError" }
    if ($LogData -match "ENOMEM")     { $hasError = $true; $errorType = "ENOMEM";     Write-Err "❌ 检测到内存不足" }
    if ($LogData -match "初始化失败|启动失败") { $hasError = $true; $errorType = "InitFailed"; Write-Err "❌ 检测到初始化失败" }

    if (-not $hasError -and $LogData -match "蓝牙功率计已启动") {
        Write-Info "🎉 部署成功！程序运行正常"
        return
    }

    if ((-not $NoFix) -and $RetryCount -lt $Retries) {
        $script:RetryCount++
        Write-Warn "尝试自动修复 (第 $RetryCount/$Retries 次)..."

        switch ($errorType) {
            "NameError"  { Write-Info "修复策略: 重新检查 BOM 并重新上传"; Check-File; Upload-File }
            "ENOMEM"     { Write-Info "修复策略: 重启设备后重试"; Start-Sleep -Seconds 3 }
            default      { Write-Info "修复策略: 重新部署"; Check-File; Upload-File }
        }

        Run-Program
        return
    }

    Write-Err "部署失败，请手动检查日志"
    exit 1
}

# ============================================================
#  主流程
# ============================================================
Write-Host ""
Write-Host "╔══════════════════════════════════════╗"
Write-Host "║   ESP32-C3 MicroPython 一键部署      ║"
Write-Host "╚══════════════════════════════════════╝"
Write-Host ""

Find-Esp32Port
Release-Port
Verify-Connection
Remove-LegacyFiles
Check-File
Upload-File
Run-Program

Write-Host ""
Write-Info "完成！设备 $SerialPort 运行中"
