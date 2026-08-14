# 暖眸 Demo 启动脚本
param(
    [string]$Scene = "medication",
    [switch]$TTS
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptArgs = @("--scene", $Scene)
if ($TTS) { $scriptArgs += "--tts" }

$script = Join-Path $PSScriptRoot "main.py"
$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    & py $script @scriptArgs
} else {
    & python $script @scriptArgs
}
