# Definitions only; no process or Add-Type side effects.
function Atomic-Receipt([string]$Path,$Value){
    if(Test-Path -LiteralPath $Path){throw 'Receipt already exists'}
    $tmp=$Path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 14))
    $stream=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
    try{[IO.File]::Move($tmp,$Path)}finally{if(Test-Path -LiteralPath $tmp){[IO.File]::Delete($tmp)}}
}
function Complete-AngularOwnership([string]$Marker,[string]$Token,[bool]$CleanupConfirmed){
    $result=@{slotBlocked=$true;error=$null}
    if(-not $CleanupConfirmed){
        if(-not (Test-Path -LiteralPath $Marker)){
            try{Atomic-Receipt $Marker @{owner='AngularVATNative01';ownershipToken=$Token;status='cleanup_unconfirmed';manualCoordinatorClearanceRequired=$true}}
            catch{$result.error='Could not restore blocked marker: '+$_.Exception.Message}
        }
        return $result
    }
    try{
        $saved=Get-Content -LiteralPath $Marker -Raw -ErrorAction Stop|ConvertFrom-Json -ErrorAction Stop
        if($saved.owner -cne 'AngularVATNative01' -or $saved.ownershipToken -cne $Token){throw 'Foreign/corrupt marker retained'}
        [IO.File]::Delete($Marker)
        $result.slotBlocked=$false
    }catch{
        $result.error=$_.Exception.Message
        # A missing marker must not turn into an apparently free slot after failure.
        if(-not (Test-Path -LiteralPath $Marker)){
            try{Atomic-Receipt $Marker @{owner='AngularVATNative01';ownershipToken=$Token;status='marker_cleanup_unresolved';manualCoordinatorClearanceRequired=$true}}
            catch{$result.error+='; could not restore marker: '+$_.Exception.Message}
        }
    }
    return $result
}
function Assert-AngularDeadline([double]$Elapsed,[int]$Total){
    if($Elapsed -ge ($Total-5)){throw 'Total deadline exhausted; final5s reserved for owned cleanup'}
}
function Get-AngularPreservation($Before){
    $result=@{preserved=$false;changed=@();error=$null}
    try{
        foreach($p in $Before.Keys){
            if(-not (Test-Path -LiteralPath $p) -or (Get-FileHash -LiteralPath $p -ErrorAction Stop).Hash.ToLowerInvariant() -ne $Before[$p]){$result.changed+= $p}
        }
        $result.preserved=($result.changed.Count -eq 0)
    }catch{$result.error=$_.Exception.Message}
    return $result
}
