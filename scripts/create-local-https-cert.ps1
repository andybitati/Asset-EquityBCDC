param(
    [string]$OutputDir = "certs",
    [string]$DnsName = "localhost",
    [int]$ValidYears = 3
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$targetDir = if ([System.IO.Path]::IsPathRooted($OutputDir)) { $OutputDir } else { Join-Path $root $OutputDir }
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$subject = [System.Security.Cryptography.X509Certificates.X500DistinguishedName]::new("CN=$DnsName")
$hash = [System.Security.Cryptography.HashAlgorithmName]::SHA256
$padding = [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
$request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new($subject, $rsa, $hash, $padding)

$serverAuthOid = [System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.1")
$oids = [System.Security.Cryptography.OidCollection]::new()
[void]$oids.Add($serverAuthOid)
$request.CertificateExtensions.Add(
    [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($oids, $false)
)
$request.CertificateExtensions.Add(
    [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true)
)
$request.CertificateExtensions.Add(
    [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
        [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature,
        $true
    )
)

$sanBuilder = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
$sanBuilder.AddDnsName($DnsName)
$sanBuilder.AddDnsName("127.0.0.1")
$sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("127.0.0.1"))
$request.CertificateExtensions.Add($sanBuilder.Build())

$notBefore = [System.DateTimeOffset]::UtcNow.AddDays(-1)
$notAfter = $notBefore.AddYears($ValidYears)
$certificate = $request.CreateSelfSigned($notBefore, $notAfter)

function Convert-ToPem([string]$Label, [byte[]]$Bytes) {
    $base64 = [System.Convert]::ToBase64String($Bytes)
    $lines = for ($index = 0; $index -lt $base64.Length; $index += 64) {
        $base64.Substring($index, [System.Math]::Min(64, $base64.Length - $index))
    }
    "-----BEGIN $Label-----`n$($lines -join "`n")`n-----END $Label-----`n"
}

function Join-Bytes([byte[][]]$Parts) {
    $length = 0
    foreach ($part in $Parts) {
        $length += $part.Length
    }
    $buffer = New-Object byte[] $length
    $offset = 0
    foreach ($part in $Parts) {
        [System.Buffer]::BlockCopy($part, 0, $buffer, $offset, $part.Length)
        $offset += $part.Length
    }
    $buffer
}

function Encode-AsnLength([int]$Length) {
    if ($Length -lt 128) {
        return [byte[]]@($Length)
    }
    $bytes = New-Object System.Collections.Generic.List[byte]
    $value = $Length
    while ($value -gt 0) {
        $bytes.Insert(0, [byte]($value -band 0xff))
        $value = $value -shr 8
    }
    [byte[]]@(0x80 -bor $bytes.Count) + [byte[]]$bytes.ToArray()
}

function Encode-AsnInteger([byte[]]$Value) {
    $start = 0
    while ($start -lt ($Value.Length - 1) -and $Value[$start] -eq 0) {
        $start++
    }
    $length = $Value.Length - $start
    $trimmed = New-Object byte[] $length
    [System.Buffer]::BlockCopy($Value, $start, $trimmed, 0, $length)
    if (($trimmed[0] -band 0x80) -ne 0) {
        $trimmed = [byte[]]@(0) + $trimmed
    }
    Join-Bytes @([byte[]]@(0x02), (Encode-AsnLength $trimmed.Length), $trimmed)
}

function Encode-AsnSequence([byte[]]$Content) {
    Join-Bytes @([byte[]]@(0x30), (Encode-AsnLength $Content.Length), $Content)
}

function Export-RsaPrivateKeyPkcs1([System.Security.Cryptography.RSA]$Rsa) {
    $parameters = $Rsa.ExportParameters($true)
    $parts = @(
        (Encode-AsnInteger ([byte[]]@(0))),
        (Encode-AsnInteger $parameters.Modulus),
        (Encode-AsnInteger $parameters.Exponent),
        (Encode-AsnInteger $parameters.D),
        (Encode-AsnInteger $parameters.P),
        (Encode-AsnInteger $parameters.Q),
        (Encode-AsnInteger $parameters.DP),
        (Encode-AsnInteger $parameters.DQ),
        (Encode-AsnInteger $parameters.InverseQ)
    )
    Encode-AsnSequence (Join-Bytes $parts)
}

$certPath = Join-Path $targetDir 'localhost-cert.pem'
$keyPath = Join-Path $targetDir 'localhost-key.pem'
$envExamplePath = Join-Path $targetDir '.env.https.example'

[System.IO.File]::WriteAllText($certPath, (Convert-ToPem "CERTIFICATE" $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)))
[System.IO.File]::WriteAllText($keyPath, (Convert-ToPem "RSA PRIVATE KEY" (Export-RsaPrivateKeyPkcs1 $rsa)))
[System.IO.File]::WriteAllText($envExamplePath, @"
ASSET_EQUITY_PORT=48620
ASSET_EQUITY_HOST=127.0.0.1
ASSET_EQUITY_OPEN_BROWSER=true
ASSET_EQUITY_SSL_CERTFILE=certs\localhost-cert.pem
ASSET_EQUITY_SSL_KEYFILE=certs\localhost-key.pem
"@)

Write-Host "Certificat créé : $certPath"
Write-Host "Clé privée créée : $keyPath"
Write-Host "Exemple .env créé : $envExamplePath"
Write-Host "Copiez les deux lignes ASSET_EQUITY_SSL_* dans le fichier .env placé à côté de AssetsEquityBCDC.exe."
