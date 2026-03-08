# Helper script to post message to Discord
param(
    [string]$MessageFile,
    [string]$ChannelId
)

$message = Get-Content $MessageFile -Raw

# Use the message tool directly via PowerShell
$escapedMessage = $message.Replace('"', '`"').Replace('$', '`$')

# Build the command
$cmd = "easyclaw"
$args = @(
    "message",
    "send",
    "--channel", "discord",
    "--target", $ChannelId,
    "--message", $message
)

& $cmd $args
