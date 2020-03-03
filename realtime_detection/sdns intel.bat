set CC=icl
set LD=xilink
call conda activate intelpython3
call python main_realtime.py
pause
::conda create -n intelpython3 -c intel python=3.6 intelpython3_full