Write-Host "`n🛡️ ShieldX Full Auto-Start Script`n" -ForegroundColor Cyan

# ==== 1️⃣ .env Check ====
$envPath = "C:\ShieldX-Bot\.env"
if (Test-Path $envPath) {
    Write-Host "✅ .env file found."
    Get-Content $envPath | ForEach-Object {
        if ($_ -match "^(.*?)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
    Write-Host "🌍 Environment variables loaded."
} else {
    Write-Host "⚠️ .env missing! Create it with your BOT_TOKEN and OWNER_ID first." -ForegroundColor Yellow
    exit
}

# ==== 2️⃣ Render Status Check ====
$renderHook = "https://api.render.com/deploy/srv-d3l9vipr0fns73f6a1g0?key=SGZEUdUPgVY"
$serviceURL = "https://shieldx-bot-1.onrender.com"
Write-Host "`n🌐 Checking Render service status..."

try {
    $resp = Invoke-WebRequest -Uri $serviceURL -Method Head -UseBasicParsing -ErrorAction SilentlyContinue
    if ($resp.StatusCode -eq 200) {
        Write-Host "✅ Render service is active."
    } else {
        Write-Host "⚠️ Render seems inactive. Attempting auto-resume..."
        Invoke-WebRequest -Uri $renderHook -Method POST -UseBasicParsing
        Write-Host "🚀 Resume request sent. Waiting 20 seconds..."
        Start-Sleep -Seconds 20
    }
} catch {
    Write-Host "⚠️ Could not reach Render, trying to wake it..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $renderHook -Method POST -UseBasicParsing
}

# ==== 3️⃣ Bot Token Check ====
if ($env:BOT_TOKEN) {
    Write-Host "`n🤖 Bot token detected. Starting local test..."
} else {
    Write-Host "❌ BOT_TOKEN not found. Please fix your .env." -ForegroundColor Red
    exit
}

# ==== 4️⃣ Start Bot ====
$botPath = "C:\ShieldX-Bot\bot.py"
if (Test-Path $botPath) {
    Write-Host "`n🌀 Starting ShieldX Bot (Python)..."
    Start-Process python -ArgumentList $botPath -NoNewWindow
    Write-Host "✅ Bot process launched."
} else {
    Write-Host "❌ bot.py not found in ShieldX-Bot folder!" -ForegroundColor Red
    exit
}

# ==== 5️⃣ Telegram Test ====
Write-Host "`n⚡ Try sending /ping or /help to your bot in Telegram."
Write-Host "✨ Auto-start complete. Your bot should now be live!`n"
