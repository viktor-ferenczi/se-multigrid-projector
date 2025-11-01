REM Location of Pulsar (because Rider does not support %AppData% in run configs)
REM This is required only by the Pulsar run config for Rider. If you are using VS, 
REM then you don't need to run this script at all.
mklink /J Pulsar "%AppData%\Pulsar"
