@echo off
echo  WARING: Must update __version__ number in __init__.py file!!!
pause

rd /s /q dist
rd /s /q build

% 打包 %
python -m build --sdist
python -m build --wheel

% 发布 %
twine upload dist\*