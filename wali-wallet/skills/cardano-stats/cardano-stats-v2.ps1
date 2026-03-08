# Cardano Stats Bot Script
# Fetches and posts hourly Cardano statistics to Discord

param(
    [string]$BlockfrostKey = $env:BLOCKFROST_API_KEY,
    [string]$ChannelId = "1478116857595695407"
)

# Configuration
$USDCxAssetId = "1f3aec8bfe7ea4fe14c5f121e2a92e301afe414147860d557cac7e345553444378"
$MinswapAPI = "https://api-mainnet-prod.minswap.org"
$CoinGeckoAPI = "https://api.coingecko.com/api/v3"
$BlockfrostAPI = "https://cardano-mainnet.blockfrost.io/api/v0"

$ErrorActionPreference = "Stop"
$logFile = Join-Path $PSScriptRoot "cardano-stats.log"
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Cardano stats fetch..." | Add-Content $logFile

Write-Host "Fetching Cardano stats..." -ForegroundColor Cyan

try {
    # 1. Fetch ADA Price from CoinGecko
    Write-Host "Fetching ADA price..." -ForegroundColor Yellow
    $adaData = Invoke-RestMethod -Uri "$CoinGeckoAPI/simple/price?ids=cardano&vs_currencies=usd&include_24hr_change=true" -Method Get
    $adaPrice = [math]::Round($adaData.cardano.usd, 3)
    $adaChange = [math]::Round($adaData.cardano.usd_24h_change, 2)
    $adaEmoji = if ($adaChange -ge 0) { ":green_circle:" } else { ":red_circle:" }
    
    Write-Host "Done ADA price" -ForegroundColor Green

    # 2. Fetch USDCx Total Supply from Blockfrost
    Write-Host "Fetching USDCx supply..." -ForegroundColor Yellow
    $headers = @{
        "project_id" = $BlockfrostKey
    }
    $usdcxData = Invoke-RestMethod -Uri "$BlockfrostAPI/assets/$USDCxAssetId" -Method Get -Headers $headers
    $usdcxSupply = [math]::Round([decimal]$usdcxData.quantity / 1000000, 0)
    $usdcxFormatted = "{0:N0}" -f $usdcxSupply
    
    Write-Host "Done USDCx" -ForegroundColor Green

    # 3. Fetch Top 10 CNTs by Liquidity
    Write-Host "Fetching top CNTs by liquidity..." -ForegroundColor Yellow
    $liquidityBody = @{
        limit = 10
        only_verified = $true
        sort_field = "liquidity"
        sort_direction = "desc"
        currency = "usd"
    } | ConvertTo-Json
    
    $liquidityData = Invoke-RestMethod -Uri "$MinswapAPI/v1/assets/metrics" -Method Post -Body $liquidityBody -ContentType "application/json"
    
    # 4. Fetch Top 10 CNTs by Volume
    Write-Host "Fetching top CNTs by volume..." -ForegroundColor Yellow
    $volumeBody = @{
        limit = 10
        only_verified = $true
        sort_field = "volume_24h"
        sort_direction = "desc"
        currency = "usd"
    } | ConvertTo-Json
    
    $volumeData = Invoke-RestMethod -Uri "$MinswapAPI/v1/assets/metrics" -Method Post -Body $volumeBody -ContentType "application/json"
    
    # 5. Fetch Top 10 CNTs by Market Cap
    Write-Host "Fetching top CNTs by market cap..." -ForegroundColor Yellow
    $marketCapBody = @{
        limit = 10
        only_verified = $true
        sort_field = "market_cap"
        sort_direction = "desc"
        currency = "usd"
    } | ConvertTo-Json
    
    $marketCapData = Invoke-RestMethod -Uri "$MinswapAPI/v1/assets/metrics" -Method Post -Body $marketCapBody -ContentType "application/json"
    
    Write-Host "Fetched all top 10 lists" -ForegroundColor Green

    # Build message parts
    $parts = @()
    $parts += "$adaEmoji **ADA:** $" + "$adaPrice ($adaChange% 24h)"
    $parts += ":moneybag: **USDCx Minted:** $" + $usdcxFormatted
    $parts += ""
    
    # Top 10 by Liquidity
    $parts += ":chart_with_upwards_trend: **Top 10 CNTs by Liquidity:**"
    $i = 1
    foreach ($asset in $liquidityData.asset_metrics) {
        $ticker = if ($asset.asset.metadata.ticker) { $asset.asset.metadata.ticker } else { $asset.asset.metadata.name }
        $liq = $asset.liquidity
        $liquidityStr = if ($liq -ge 1000000) { 
            "$" + ([math]::Round($liq / 1000000, 1)).ToString() + "M" 
        } else { 
            "$" + ([math]::Round($liq / 1000, 0)).ToString() + "K" 
        }
        $change = [math]::Round($asset.price_change_24h, 1)
        $changeStr = if ($change -ge 0) { "+$change%" } else { "$change%" }
        $parts += "$i. $ticker - $liquidityStr ($changeStr)"
        $i++
    }
    
    # Top 10 by Volume
    $parts += ""
    $parts += ":bar_chart: **Top 10 CNTs by 24h Volume:**"
    $i = 1
    foreach ($asset in $volumeData.asset_metrics) {
        $ticker = if ($asset.asset.metadata.ticker) { $asset.asset.metadata.ticker } else { $asset.asset.metadata.name }
        $vol = $asset.volume_24h
        $volumeStr = if ($vol -ge 1000000) { 
            "$" + ([math]::Round($vol / 1000000, 1)).ToString() + "M" 
        } else { 
            "$" + ([math]::Round($vol / 1000, 0)).ToString() + "K" 
        }
        $change = [math]::Round($asset.price_change_24h, 1)
        $changeStr = if ($change -ge 0) { "+$change%" } else { "$change%" }
        $parts += "$i. $ticker - $volumeStr ($changeStr)"
        $i++
    }
    
    # Top 10 by Market Cap
    $parts += ""
    $parts += ":money_with_wings: **Top 10 CNTs by Market Cap:**"
    $i = 1
    foreach ($asset in $marketCapData.asset_metrics) {
        $ticker = if ($asset.asset.metadata.ticker) { $asset.asset.metadata.ticker } else { $asset.asset.metadata.name }
        $mc = $asset.market_cap
        $marketCapStr = if ($mc -ge 1000000) { 
            "$" + ([math]::Round($mc / 1000000, 1)).ToString() + "M" 
        } else { 
            "$" + ([math]::Round($mc / 1000, 0)).ToString() + "K" 
        }
        $change = [math]::Round($asset.price_change_24h, 1)
        $changeStr = if ($change -ge 0) { "+$change%" } else { "$change%" }
        $parts += "$i. $ticker - $marketCapStr ($changeStr)"
        $i++
    }
    
    $message = $parts -join "`n"
    
    Write-Host "`n=== FORMATTED MESSAGE ===" -ForegroundColor Magenta
    Write-Host $message
    Write-Host "========================`n" -ForegroundColor Magenta
    
    # Post to Discord
    Write-Host "Posting to Discord..." -ForegroundColor Yellow
    
    # Save message to temp file
    $tempFile = Join-Path $PSScriptRoot "last-message.txt"
    $message | Set-Content -Path $tempFile -NoNewline -Encoding UTF8
    
    # Use Python helper to post (handles multiline properly)
    $pythonScript = Join-Path $PSScriptRoot "post-message.py"
    $pythonExe = "C:\Users\thisc\AppData\Local\Programs\Python\Python311\python.exe"
    $pythonOutput = & $pythonExe $pythonScript $ChannelId $tempFile 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR posting to Discord: $pythonOutput" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Discord post result: $pythonOutput" -ForegroundColor Green
    }
    
    Write-Host "Posted to cardano-stats!" -ForegroundColor Green

} catch {
    $errorMsg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $($_.Exception.Message)"
    $errorMsg | Add-Content $logFile
    $_.ScriptStackTrace | Add-Content $logFile
    Write-Host "Error occurred" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Completed successfully" | Add-Content $logFile
