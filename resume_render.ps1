Write-Host "🛡️ ShieldX Render Auto-Resume Script"
$renderHook = "https://api.render.com/deploy/srv-d3l9vipr0fns73f6a1g0?key=SGZEUdUPgVY"

try {
    Write-Host "⏳ Checking Render service..."
    $response = Invoke-WebRequest -Uri "https://shieldx-bot-1.onrender.com" -Method Head -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Service is already live! No action needed."
    } else {
        Write-Host "⚠️ Service seems inactive. Sending resume signal..."
        Invoke-WebRequest -Uri $renderHook -Method POST -UseBasicParsing
        Write-Host "🚀 Resume request sent. Wait 15–20 seconds, then run test_shieldx.ps1"
    }
}
catch {
    Write-Host "❌ Error contacting Render API. It may be suspended."
    Write-Host "💡 Try resuming manually from https://render.com"
}
