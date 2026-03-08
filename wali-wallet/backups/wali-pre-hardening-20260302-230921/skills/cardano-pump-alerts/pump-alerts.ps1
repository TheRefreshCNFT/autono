# Cardano Pump Alert Bot
# Monitors CNT tokens for rapid price increases

param(
    [string]$ChannelId = "1478117022448488579",
    [string]$StateFile = "C:\Users\thisc\.easyclaw\workspace\skills\cardano-pump-alerts\pump-state.json"
)

$MinswapAPI = "https://api-mainnet-prod.minswap.org"
$PumpThreshold = 10  # Percentage
$TimeWindow = 15     # Minutes
$FollowUpDelay = 5   # Minutes

Write-Host "Checking for pumps..." -ForegroundColor Cyan

try {
    # Load or initialize state
    if (Test-Path $StateFile) {
        $state = Get-Content $StateFile -Raw | ConvertFrom-Json
        # Ensure properties exist
        if (-not $state.priceHistory) { $state | Add-Member -MemberType NoteProperty -Name priceHistory -Value @{} -Force }
        if (-not $state.activeAlerts) { $state | Add-Member -MemberType NoteProperty -Name activeAlerts -Value @{} -Force }
    } else {
        $state = [PSCustomObject]@{
            priceHistory = [PSCustomObject]@{}
            activeAlerts = [PSCustomObject]@{}
            lastCleanup = (Get-Date).ToUniversalTime().ToString("o")
        }
    }

    # Clean up old entries (older than 1 hour)
    $cutoffTime = (Get-Date).AddHours(-1)
    $cleanedHistory = [PSCustomObject]@{}
    if ($state.priceHistory.PSObject.Properties.Count -gt 0) {
        foreach ($key in $state.priceHistory.PSObject.Properties.Name) {
            $entry = $state.priceHistory.$key
            $entryTime = if ($entry -is [array] -and $entry.Count -gt 0) { 
                [DateTime]$entry[0].timestamp 
            } else { 
                (Get-Date).AddHours(-2) 
            }
            if ($entryTime -gt $cutoffTime) {
                $cleanedHistory | Add-Member -MemberType NoteProperty -Name $key -Value $entry -Force
            }
        }
    }
    $state.priceHistory = $cleanedHistory

    # Fetch top 50 tokens by volume
    Write-Host "Fetching token prices..." -ForegroundColor Yellow
    $body = @{
        limit = 50
        only_verified = $true
        sort_field = "volume_24h"
        sort_direction = "desc"
        currency = "usd"
    } | ConvertTo-Json

    $data = Invoke-RestMethod -Uri "$MinswapAPI/v1/assets/metrics" -Method Post -Body $body -ContentType "application/json"
    
    $currentTime = Get-Date
    $alerts = @()
    $followUps = @()

    foreach ($asset in $data.asset_metrics) {
        $ticker = if ($asset.asset.metadata.ticker) { $asset.asset.metadata.ticker } else { $asset.asset.metadata.name }
        $assetId = $asset.asset.currency_symbol + $asset.asset.token_name
        $currentPrice = $asset.price
        
        # Skip if price is 0 or null
        if (-not $currentPrice -or $currentPrice -eq 0) { continue }

        # Store current price in history
        if (-not $state.priceHistory.$assetId) {
            $state.priceHistory | Add-Member -MemberType NoteProperty -Name $assetId -Value @() -Force
        }
        
        # Convert to array if needed
        $history = @($state.priceHistory.$assetId)
        $history += @{
            price = $currentPrice
            timestamp = $currentTime.ToUniversalTime().ToString("o")
        }
        
        # Keep only last 30 minutes of data
        $recentHistory = $history | Where-Object { 
            [DateTime]$_.timestamp -gt $currentTime.AddMinutes(-30) 
        }
        $state.priceHistory.$assetId = $recentHistory

        # Check for pump (compare to 10 minutes ago)
        $tenMinAgo = $currentTime.AddMinutes(-$TimeWindow)
        $oldPrice = $recentHistory | Where-Object { 
            [DateTime]$_.timestamp -le $tenMinAgo 
        } | Select-Object -First 1

        if ($oldPrice) {
            $priceChange = (($currentPrice - $oldPrice.price) / $oldPrice.price) * 100
            
            # Check if this token needs a follow-up
            if ($state.activeAlerts.$assetId) {
                $alertTime = [DateTime]$state.activeAlerts.$assetId.alertTime
                $minutesSinceAlert = ($currentTime - $alertTime).TotalMinutes
                
                if ($minutesSinceAlert -ge $FollowUpDelay) {
                    # Time for follow-up
                    $alertPrice = $state.activeAlerts.$assetId.price
                    $followUpChange = (($currentPrice - $alertPrice) / $alertPrice) * 100
                    
                    $followUps += @{
                        ticker = $ticker
                        currentPrice = $currentPrice
                        alertPrice = $alertPrice
                        change = $followUpChange
                        volume = $asset.volume_24h
                    }
                    
                    # Remove from active alerts
                    $state.activeAlerts.PSObject.Properties.Remove($assetId)
                }
            }
            # Check for new pump
            elseif ($priceChange -ge $PumpThreshold) {
                # New pump detected!
                $alerts += @{
                    ticker = $ticker
                    oldPrice = $oldPrice.price
                    newPrice = $currentPrice
                    change = $priceChange
                    volume = $asset.volume_24h
                    liquidity = $asset.liquidity
                }
                
                # Add to active alerts
                if (-not $state.activeAlerts.$assetId) {
                    $state.activeAlerts | Add-Member -MemberType NoteProperty -Name $assetId -Value @{} -Force
                }
                $state.activeAlerts.$assetId = @{
                    price = $currentPrice
                    alertTime = $currentTime.ToUniversalTime().ToString("o")
                    ticker = $ticker
                }
            }
        }
    }

    # Post alerts to Discord
    foreach ($alert in $alerts) {
        $oldPriceStr = "`$" + [math]::Round($alert.oldPrice, 4)
        $newPriceStr = "`$" + [math]::Round($alert.newPrice, 4)
        $changeStr = "+" + [math]::Round($alert.change, 1) + "%"
        $volumeStr = if ($alert.volume -ge 1000000) { 
            "`$" + [math]::Round($alert.volume / 1000000, 1) + "M" 
        } else { 
            "`$" + [math]::Round($alert.volume / 1000, 0) + "K" 
        }
        $liqStr = if ($alert.liquidity -ge 1000000) { 
            "`$" + [math]::Round($alert.liquidity / 1000000, 1) + "M" 
        } else { 
            "`$" + [math]::Round($alert.liquidity / 1000, 0) + "K" 
        }
        
        $message = ":fire: **PUMP ALERT!** :fire:`n"
        $message += "**Token:** " + $alert.ticker + "`n"
        $message += "**Price:** $oldPriceStr → $newPriceStr ($changeStr in 10min)`n"
        $message += "**Volume 24h:** $volumeStr`n"
        $message += "**Liquidity:** $liqStr`n"
        $message += "**Exchange:** Minswap"
        
        Write-Host "PUMP ALERT: $($alert.ticker) $changeStr" -ForegroundColor Red
        & easyclaw message send --channel discord --target $ChannelId --message $message
    }

    # Post follow-ups to Discord
    foreach ($followUp in $followUps) {
        $currentPriceStr = "`$" + [math]::Round($followUp.currentPrice, 4)
        $changeStr = [math]::Round($followUp.change, 1)
        $changeDisplay = if ($changeStr -ge 0) { "+$changeStr%" } else { "$changeStr%" }
        $status = if ($changeStr -ge 0) { ":green_circle: Still pumping!" } else { ":red_circle: Cooling off" }
        
        $message = ":bar_chart: **UPDATE:** " + $followUp.ticker + "`n"
        $message += "**Price now:** $currentPriceStr ($changeDisplay since alert)`n"
        $message += "**Status:** $status"
        
        Write-Host "FOLLOW-UP: $($followUp.ticker) $changeDisplay" -ForegroundColor Yellow
        & easyclaw message send --channel discord --target $ChannelId --message $message
    }

    # Save state
    $state | ConvertTo-Json -Depth 10 | Set-Content $StateFile
    
    if ($alerts.Count -gt 0 -or $followUps.Count -gt 0) {
        Write-Host "Posted $($alerts.Count) alerts and $($followUps.Count) follow-ups" -ForegroundColor Green
    } else {
        Write-Host "No pumps detected" -ForegroundColor Gray
    }

} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
