param([string]$Eingabe, [string]$Vorlage)
$ErrorActionPreference = 'Stop'

function Complete-Vorlage($Dokument, [string]$Vorlage) {
    # Verzeichnisse heben semiHidden ihrer Formatvorlagen auf, Visibility wahr heisst verborgen;
    # InUse zuerst, sonst legt das Lesen von Visibility alle latenten Formatvorlagen an
    $verborgen = @($Dokument.Styles | Where-Object { $_.InUse -and $_.Visibility })
    # die erste Runde verschiebt Seiten, die zweite traegt deren Seitenzahlen ein; BIBLIOGRAPHY
    # (Typ 97) haengt nicht vom Umbruch ab, jedes Aktualisieren legt ein w:div in webSettings an
    foreach ($runde in 1..2) {
        @($Dokument.TablesOfContents) + @($Dokument.TablesOfFigures) | ForEach-Object { $_.Update() }
        foreach ($feld in $Dokument.Fields) {
            if (($runde -eq 1 -or $feld.Type -ne 97) -and -not $feld.Update()) {
                throw "Feld nicht aktualisiert: $($feld.Code.Text)"
            }
        }
        $Dokument.Repaginate()
    }
    foreach ($stil in @($verborgen | Where-Object { -not $_.Visibility })) { $stil.Visibility = $true }
    $Dokument.SaveAs2($Vorlage, 14, $false, '', $false)
    # SaveAs2 traegt Normal.dotm als Template in app.xml ein, erst ein zweites Speichern leert es
    $Dokument.Saved = $false
    $Dokument.Save()
}

if ($MyInvocation.InvocationName -ne '.') {
    $offen = @(Get-Process WINWORD -ErrorAction SilentlyContinue).Id
    $word = New-Object -ComObject Word.Application
    # Quit ohne Speichern darf nur die eigene Instanz treffen, nie ein offenes Word
    if (-not (Get-Process WINWORD | Where-Object Id -notin $offen)) { throw 'keine eigene Instanz' }
    try {
        $word.DisplayAlerts = 0
        $doc = $word.Documents.Open($Eingabe, $false, $false, $false)
        Complete-Vorlage $doc $Vorlage
    } finally {
        $word.NormalTemplate.Saved = $true
        $word.Quit([ref]0)
    }
}
