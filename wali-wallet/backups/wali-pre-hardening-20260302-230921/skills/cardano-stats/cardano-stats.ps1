# Cardano Stats Bot Script
# Fetches and posts hourly Cardano statistics to Discord

param(
    [string]$BlockfrostKey = $env:BLOCKFROST_API_KEY,
    [string]$ChannelId = "1478116857595695407"
)

# Configuration
$USDCxPolicyId = "1f3aec8bfe7ea4fe14c5f121e2a92e301afe414147860d557cac7e34"
$MinswapAPI = "https://api-mainnet-prod.minswap.org"
$CoinGeckoAPI = "https://api.coingecko.com/api/v3"
$BlockfrostAPI = "https://cardano-mainnet.blockfrost.io/api/v0"

Write-Host "🦞 Fetching Cardano stats..." -ForegroundColor Cyan

try {
    # 1. Fetch ADA Price from CoinGecko
    Write-Host "Fetching ADA price..." -ForegroundColor Yellow
    $adaData = Invoke-RestMethod -Uri "$CoinGeckoAPI/simple/price?ids=cardano&vs_currencies=usd&include_24hr_change=true" -Method Get
    $adaPrice = [math]::Round($adaData.cardano.usd, 2)
    $adaChange = [math]::Round($adaData.cardano.usd_24h_change, 2)
    $adaEmoji = if ($adaChange -ge 0) { ":green_circle:" } else { ":red_circle:" }
    
    Write-Host "Done ADA: `$$adaPrice ($adaChange percent)" -ForegroundColor Green

    # 2. Fetch USDCx Total Supply from Blockfrost
    Write-Host "Fetching USDCx supply..." -ForegroundColor Yellow
    $headers = @{
        "project_id" = $BlockfrostKey
    }
    $usdcxData = Invoke-RestMethod -Uri "$BlockfrostAPI/assets/$USDCxPolicyId" -Method Get -Headers $headers
    $usdcxSupply = [math]::Round([decimal]$usdcxData.quantity / 1000000, 0) # Convert from lovelace
    $usdcxFormatted = "{0:N0}" -f $usdcxSupply
    
    Write-Host "✓ USDCx: `$$usdcxFormatted" -ForegroundColor Green

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
    
    Write-Host "✓ Fetched all top 10 lists" -ForegroundColor Green

    # Format the Discord message
    $message = "$adaEmoji **ADA:** ```$$adaPrice ($adaChange% 24h)```n"
    $message += ":moneybag: **USDCx Minted:** `$$usdcxFormatted`n`n"
    
    # Top 10 by Liquidity
    $message += ":chart_with_upwards_trend: **Top 10 CNTs by Liquidity:**`n"
    $i = 1
    foreach ($asset in $liquidityData.asset_metrics) {
        $ticker = $asset.asset.metadata.ticker
        if (-not $ticker) { $ticker = $asset.asset.metadata.name }
        $liquidity = if ($asset.liquidity -ge 1000000) { 
            "`$" + [math]::Round($asset.liquidity / 1000000, 1) + "M" 
        } else { 
            "`$" + [math]::Round($asset.liquidity / 1000, 0) + "K" 
        }
        $change = [math]::Round($asset.price_change_24h, 1)
        $changeEmoji = if ($change -ge 0) { "+" } else { "" }
        $message += "$i. $ticker - $liquidity ($changeEmoji$change%)`n"
        $i++
    }
    
    # Top 10 by Volume
    $message += "`n:bar_chart: **Top 10 CNTs by 24h Volume:**`n"
    $i = 1
    foreach ($asset in $volumeData.asset_metrics) {
        $ticker = $asset.asset.metadata.ticker
        if (-not $ticker) { $ticker = $asset.asset.metadata.name }
        $volume = if ($asset.volume_24h -ge 1000000) { 
            "`$" + [math]::Round($asset.volume_24h / 1000000, 1) + "M" 
        } else { 
            "`$" + [math]::Round($asset.volume_24h / 1000, 0) + "K" 
        }
        $change = [math]::Round($asset.price_change_24h, 1)
        $changeEmoji = if ($change -ge 0) { "+" } else { "" }
        $message += "$i. $ticker - $volume ($changeEmoji$change%)`n"
        $i++
    }
    
    # Top 10 by Market Cap
    $message += "`n:money_with_wings: **Top 10 CNTs by Market Cap:**`n"
    $i = 1
    foreach ($asset in $marketCapData.asset_metrics) {
        $ticker = $asset.asset.metadata.ticker
        if (-not $ticker) { $ticker = $asset.asset.metadata.name }
        $marketCap = if ($asset.market_cap -ge 1000000) { 
            "`$" + [math]::Round($asset.market_cap / 1000000, 1) + "M" 
        } else { 
            "`$" + [math]::Round($asset.market_cap / 1000, 0) + "K" 
        }
        $change = [math]::Round($asset.price_change_24h, 1)
        $changeEmoji = if ($change -ge 0) { "+" } else { "" }
        $message += "$i. $ticker - $marketCap ($changeEmoji$change%)`n"
        $i++
    }
    
    Write-Host "`n=== FORMATTED MESSAGE ===" -ForegroundColor Magenta
    Write-Host $message
    Write-Host "========================`n" -ForegroundColor Magenta
    
    # Post to Discord
    Write-Host "Posting to Discord..." -ForegroundColor Yellow
    & easyclaw message send --channel discord --target $ChannelId --message $message
    
    Write-Host "✓ Posted to #cardano-stats!" -ForegroundColor Green

} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
