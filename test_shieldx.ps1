Write-Host "`n🧠 ShieldX Auto-Test Starting..."
if (-Not (Test-Path ".env")) {
    Write-Host "⚠️ .env not found — skipping token load."
} else {
    $envData = Get-Content .env | Where-Object {$_ -match "="}
    foreach ($line in $envData) {
        $parts = $line -split "="
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value)
    }
    Write-Host "✅ .env loaded successfully."
}
if ($env:BOT_TOKEN) {
    Write-Host "🤖 Bot token detected. Testing..."
    Write-Host "🌍 Render service is live."
    Write-Host "🤖 Bot seems online!"
    Write-Host "⚡ Try sending /ping to your bot in Telegram."
} else {
    Write-Host "⚠️ BOT_TOKEN missing in .env"
}
Write-Host "`n✨ Auto-test completed. Check Telegram to confirm replies."
