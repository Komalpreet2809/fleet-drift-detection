<#
  Fleet Configuration Drift Detection - control script.

  .\run.ps1 up                     create the machines (Terraform) and configure them (Ansible)
  .\run.ps1 deploy                 re-apply all Ansible configuration
  .\run.ps1 status                 fleet drift report (checks every machine right now)
  .\run.ps1 break node2 [what]     make a manual change on a machine (drift), see list below
  .\run.ps1 fix [node2]            run Ansible to put the machine(s) back to the baseline
  .\run.ps1 auto on|off            switch automatic remediation by Nagios on or off
  .\run.ps1 log                    show what auto-remediation has done
  .\run.ps1 shell node2            open a terminal on a machine (to make changes by hand)
  .\run.ps1 infra                  check for infrastructure drift with terraform plan
  .\run.ps1 open                   open Nagios and the node websites in the browser
  .\run.ps1 test                   run the automated tests
  .\run.ps1 down                   delete everything Terraform created

  break options: config | service | website | permissions | ssh | package | all
#>
param(
    [Parameter(Position = 0)] [string] $Command = "help",
    [Parameter(Position = 1)] [string] $Target = "",
    [Parameter(Position = 2)] [string] $What = "config"
)

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
$TfDir = Join-Path $Root "terraform"
$Playbooks = "/opt/drift/ansible"

function Say($text, $color = "Cyan") { Write-Host "`n==> $text" -ForegroundColor $color }

function Invoke-Control([string[]] $cmd) {
    & docker exec control @cmd | Out-Host
}

function Assert-Node($node) {
    if ($node -notmatch '^node\d$') { throw "Give a machine name, e.g. node2" }
}

switch ($Command) {
    "up" {
        Say "Terraform: creating the network, machines and SSH keys"
        terraform -chdir="$TfDir" init -input=false | Out-Null  # quiet; errors still show
        terraform -chdir="$TfDir" apply -auto-approve -input=false
        if ($LASTEXITCODE -ne 0) { throw "terraform apply failed" }
        Say "Ansible: configuring the fleet and installing Nagios"
        Invoke-Control @("ansible-playbook", "$Playbooks/site.yml")
        Say "Ready. Nagios: http://localhost:8090/nagios4  (nagiosadmin / drift123)" "Green"
    }
    "deploy" {
        Say "Ansible: applying the full configuration"
        Invoke-Control @("ansible-playbook", "$Playbooks/site.yml")
    }
    "status" {
        Invoke-Control @("drift-report", "--live")
    }
    "break" {
        Assert-Node $Target
        $changes = @{
            "config"      = "sed -i 's/max_connections = 100/max_connections = 9999/; s/debug_mode = off/debug_mode = on/' /etc/fleet/app.conf"
            "service"     = "service nginx stop"
            "website"     = "echo '<h1 style=color:red>Hacked by a careless admin</h1>' > /var/www/html/index.html"
            "permissions" = "chmod 777 /etc/fleet/app.conf"
            "ssh"         = "echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config.d/10-baseline.conf"
            "package"     = "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq telnet >/dev/null"
        }
        $list = if ($What -eq "all") { $changes.Keys } else { @($What) }
        foreach ($item in $list) {
            if (-not $changes.ContainsKey($item)) { throw "Unknown change '$item'. Use: $($changes.Keys -join ', '), all" }
            Say "Manual change on ${Target}: $item" "Yellow"
            Write-Host "    $($changes[$item])" -ForegroundColor DarkGray
            & docker exec $Target bash -c $changes[$item]
        }
        Write-Host "`nNagios will detect this within about a minute. Watch: http://localhost:8090/nagios4" -ForegroundColor Yellow
    }
    "fix" {
        $limit = if ($Target) { Assert-Node $Target; @("--limit", $Target) } else { @() }
        Say "Ansible: restoring the baseline $(if ($Target) { "on $Target" } else { 'on all machines' })"
        Invoke-Control (@("ansible-playbook", "$Playbooks/baseline.yml") + $limit)
    }
    "auto" {
        if ($Target -eq "on") {
            Invoke-Control @("bash", "-c", "echo enabled > /var/lib/drift/auto_remediate && chown nagios:nagios /var/lib/drift/auto_remediate")
            Say "Auto-remediation ON - Nagios will run Ansible to undo drift automatically" "Green"
        } elseif ($Target -eq "off") {
            Invoke-Control @("rm", "-f", "/var/lib/drift/auto_remediate")
            Say "Auto-remediation OFF - Nagios will only alert; fix with .\run.ps1 fix <node>" "Yellow"
        } else { throw "Use: .\run.ps1 auto on   or   .\run.ps1 auto off" }
    }
    "log" {
        Invoke-Control @("tail", "-n", "40", "/var/lib/drift/remediation.log")
    }
    "shell" {
        Assert-Node $Target
        & docker exec -it $Target bash
    }
    "infra" {
        Say "Terraform: comparing real infrastructure with the code"
        terraform -chdir="$TfDir" plan -detailed-exitcode -input=false
        switch ($LASTEXITCODE) {
            0 { Say "No infrastructure drift." "Green" }
            2 { Say "Infrastructure drift found (see plan above). Fix it with: .\run.ps1 up" "Red" }
            default { Say "terraform plan failed" "Red" }
        }
    }
    "open" {
        Start-Process "http://localhost:8090/nagios4"
        8091..8093 | ForEach-Object { Start-Process "http://localhost:$_" }
    }
    "test" {
        Say "Unit tests (drift check logic)"
        python -m pytest -q (Join-Path $Root "tests")
        Say "Terraform validate"
        terraform -chdir="$TfDir" validate
        Say "Ansible syntax check"
        Invoke-Control @("ansible-playbook", "--syntax-check", "$Playbooks/site.yml")
    }
    "down" {
        Say "Terraform: deleting all lab machines" "Yellow"
        terraform -chdir="$TfDir" destroy -auto-approve -input=false
    }
    default {
        Get-Content $PSCommandPath -TotalCount 19 | Select-Object -Skip 1 | Write-Host
    }
}
