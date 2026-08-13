# Aggiorna arbitro, formazioni, quote estese e stime sui giocatori.
#
# PERCHE' NON E' UN WORKFLOW DI GITHUB. Questi due job non parlano con un'API
# via HTTP: invocano il binario `sofascore-pp-cli`, che sta nella library
# locale e NON e' nel repository. Su un runner di GitHub `disponibile()`
# tornerebbe falso e il job non scriverebbe niente — una schedulazione che
# sembra funzionare e non funziona e' peggio di nessuna schedulazione.
# Quando e se il binario verra' distribuito, questo script diventa un workflow
# in tre righe.
#
# PERCHE' DUE VOLTE AL GIORNO, e non una.
#
# Le due cose che questo script raccoglie compaiono TARDI:
#
#   * l'arbitro viene designato uno o due giorni prima. Alla prima passata su
#     trenta partite ne aveva una sola;
#   * le formazioni nascono PREVISTE con giorni d'anticipo e diventano
#     UFFICIALI vicino al calcio d'inizio.
#
# Una passata larga al mattino prende il grosso; una ravvicinata la sera
# raccoglie arbitri designati nel frattempo e formazioni ormai definitive.
# Il campo `ore_prima` registra quale delle due ha scritto cosa, quindi la
# pagina sa sempre quanto e' fresco quel che mostra.
#
# USO
#   powershell -ExecutionPolicy Bypass -File scripts\aggiorna_sofascore.ps1
#   powershell ... -File scripts\aggiorna_sofascore.ps1 -Finestra 1 -SoloImminenti
#
# Con -SoloImminenti la finestra si stringe: e' la passata della sera, che
# serve a rinfrescare le partite di oggi e domani, non a ripescare quelle di
# giovedi'.

param(
    [int]$Finestra = 4,
    [switch]$SoloImminenti,
    [string]$Progetto = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Continue'

if ($SoloImminenti) { $Finestra = 1 }

Set-Location $Progetto

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host "[$stamp] aggiornamento Sofascore, finestra $Finestra giorni"

# 1) Arbitro, formazioni, quote estese.
python -m pronostici.jobs.sofascore --window-days $Finestra
$esitoUno = $LASTEXITCODE

# 2) Stime sui giocatori. Dipende dal primo: senza formazioni non c'e'
#    nessuno di cui stimare qualcosa. Se il primo fallisce, il secondo
#    lavorerebbe su dati vecchi, quindi non parte.
if ($esitoUno -eq 0) {
    python -m pronostici.jobs.giocatori --window-days $Finestra
    $esitoDue = $LASTEXITCODE
} else {
    Write-Host "il job sofascore e' fallito (codice $esitoUno): salto le stime sui giocatori"
    $esitoDue = $esitoUno
}

# 3) Il sito si ricostruisce solo se qualcosa e' cambiato davvero: i job
#    scrivono i file solo quando la sostanza cambia, quindi un build a vuoto
#    sarebbe lavoro inutile. Qui si ricostruisce sempre perche' distinguere
#    costa piu' del build stesso — ma se un giorno pesera', la condizione e'
#    `days_written` non vuoto nel report JSON dei due job.
if ($esitoUno -eq 0 -and $esitoDue -eq 0) {
    Push-Location (Join-Path $Progetto 'frontend')
    npm run build
    $esitoBuild = $LASTEXITCODE
    Pop-Location
    if ($esitoBuild -ne 0) {
        Write-Host "build del sito fallito (codice $esitoBuild)"
        exit $esitoBuild
    }
}

exit ([Math]::Max($esitoUno, $esitoDue))
