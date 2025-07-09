# Script to remove specified host entries from SSH known_hosts file
# Created: 2025-04-22

# Path to the .env file in the parent directory
$envFilePath = "$PSScriptRoot\../.env"

# Default host to remove if .env file doesn't exist or doesn't contain the variable
$hostToRemove = $null

# Read from .env file if it exists
if (Test-Path $envFilePath) {
    Get-Content $envFilePath | ForEach-Object {
        if ($_ -match '^SSH_HOST_TO_REMOVE=(.*)$') {
            $hostToRemove = $matches[1]
        }
    }
}

if ($hostToRemove -eq $null) {
    Write-Host "SSH_HOST_TO_REMOVE variable not found in .env file"
    exit
}

Write-Host "Will remove entries for host: $hostToRemove"

# Path to the known_hosts file
$knownHostsPath = "$env:USERPROFILE\.ssh\known_hosts"

# Check if the known_hosts file exists
if (Test-Path $knownHostsPath) {
    Write-Host "Found known_hosts file at: $knownHostsPath"

    # Read the current content
    $content = Get-Content $knownHostsPath

    # Count original entries
    $originalCount = $content.Count
    Write-Host "Original entry count: $originalCount"

    # Filter out entries containing the specified host
    $escapedHost = [regex]::Escape($hostToRemove)
    $newContent = $content | Where-Object { $_ -notmatch $escapedHost }

    # Count entries after filtering
    $newCount = $newContent.Count
    $removedCount = $originalCount - $newCount

    # Only write back if entries were actually removed
    if ($removedCount -gt 0) {
        # Write the filtered content back to the file
        $newContent | Set-Content $knownHostsPath
        Write-Host "Successfully removed $removedCount entries for $hostToRemove"
    } else {
        Write-Host "No entries found for $hostToRemove"
    }
} else {
    Write-Host "known_hosts file not found at: $knownHostsPath"
    Write-Host "No changes were made."
}
