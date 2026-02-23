$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$sparkSubmit = Join-Path $projectRoot "spark-4.1.1-bin-hadoop3\bin\spark-submit.cmd"
$hadoopHome = Join-Path $projectRoot "hadoop"
$streamingScript = Join-Path $projectRoot "src\streaming_app.py"
$checkpointRoot = Join-Path $projectRoot "checkpoints\crypto_runtime"
$checkpointMode = if ($env:CHECKPOINT_MODE) { $env:CHECKPOINT_MODE.ToLower() } else { "fresh" }
$checkpointDir = if ($checkpointMode -eq "reuse") {
    $checkpointRoot
} else {
    Join-Path $checkpointRoot ("run_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
}
$kafkaPackage = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1"
$driverHost = "127.0.0.1"
$driverBindAddress = "127.0.0.1"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}
if (-not (Test-Path $sparkSubmit)) {
    throw "spark-submit not found: $sparkSubmit"
}
if (-not (Test-Path $hadoopHome)) {
    throw "Hadoop directory not found: $hadoopHome"
}

$hadoopHomeForward = $hadoopHome -replace '\\', '/'
New-Item -ItemType Directory -Path $checkpointDir -Force | Out-Null

$env:PYSPARK_PYTHON = $pythonExe
$env:PYSPARK_DRIVER_PYTHON = $pythonExe
$env:HADOOP_HOME = $hadoopHome
$env:CHECKPOINT_LOCATION = $checkpointDir
$env:KAFKA_STARTING_OFFSETS = "latest"
$env:SPARK_LOCAL_IP = $driverBindAddress
$env:SPARK_LOCAL_HOSTNAME = "localhost"
$env:PATH = "$hadoopHome\bin;$env:PATH"

$args = @(
    "--packages", $kafkaPackage,
    "--conf", "spark.sql.streaming.metricsEnabled=false",
    "--conf", "spark.driver.host=$driverHost",
    "--conf", "spark.driver.bindAddress=$driverBindAddress",
    "--conf", "spark.driver.extraJavaOptions=-Dhadoop.home.dir=$hadoopHomeForward",
    "--conf", "spark.executor.extraJavaOptions=-Dhadoop.home.dir=$hadoopHomeForward",
    $streamingScript
)

& $sparkSubmit @args
