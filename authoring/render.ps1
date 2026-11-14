$ErrorActionPreference='Stop'
$reportPath=Join-Path $PSScriptRoot '不同工具契约下LLM_Agent非幂等操作失败恢复的决策边界研究.docx'
$qaDirectory=Join-Path $PSScriptRoot 'qa'
New-Item -ItemType Directory -Path $qaDirectory -Force | Out-Null
$pdfPath=Join-Path $qaDirectory 'report.pdf'
$wordApp=$null
$reportDoc=$null
try {
 $wordApp=New-Object -ComObject Word.Application
 $wordApp.Visible=$false
 $wordApp.DisplayAlerts=0
 $reportDoc=$wordApp.Documents.Open($reportPath,$false,$false)
 $reportDoc.Fields.Update() | Out-Null
 foreach ($reportToc in $reportDoc.TablesOfContents) {$reportToc.Update()}
 $reportDoc.Repaginate()
 foreach ($reportToc in $reportDoc.TablesOfContents) {$reportToc.UpdatePageNumbers()}
 $reportDoc.Fields.Update() | Out-Null
 $reportDoc.Repaginate()
 $pages=$reportDoc.ComputeStatistics(2)
 $reportDoc.Save()
 $reportDoc.ExportAsFixedFormat($pdfPath,17)
 [pscustomobject]@{Pages=$pages;TocCount=$reportDoc.TablesOfContents.Count;Pdf=$pdfPath} | ConvertTo-Json
} finally {
 if ($null -ne $reportDoc) {$reportDoc.Close(0)}
 if ($null -ne $wordApp) {$wordApp.Quit()}
}
