# Фактическая среда этапа 1, 2026-11-01

Проверки выполнены в локальном worktree; сетевые операции и часть sysctl ограничены sandbox. Наличие файла/manifest не означает успешного запуска модели.

| Компонент | Наблюдение | Готовность |
|---|---|---|
| ОС | macOS 26.6.2, build 25G83, arm64 | доступна |
| Компьютер | MacBook Air Mac14,2, Apple M2, 8 CPU cores (4+4), 8 GB unified RAM, 10 GPU cores, Metal supported; `system_profiler SPHardwareDataType SPDisplaysDataType` | ресурсы зафиксированы; пригодность модели ещё не подтверждена |
| Java | Temurin OpenJDK 17.0.2+8, 64-Bit Server VM | lab2 suite прошёл |
| Python по `python3` | 3.9.6 | ниже требования ≥3.10; не использовать для optimizer |
| `/opt/homebrew/bin/python3.11` | 3.11.18 | подходит по версии |
| `/usr/local/bin/python3.11` | 3.11.5 | также доступен |
| OWL API | 4.5.29, закреплённый JAR | успешно использован |
| HermiT | 1.4.3.456, закреплённый JAR | успешно использован |
| Protégé Desktop 5.6.9 | не найден в /Applications и ~/Applications, поиск maxdepth 2 | GUI-проверки недоступны; не заявлены выполненными |
| Ollama CLI | 0.40.9, /usr/local/bin/ollama; приложение Ollama.app установлено | клиент доступен |
| Ollama API | GET http://localhost:11434/api/tags → curl exit 7 (connection failed); ollama --version предупреждает об отсутствии соединения | сервер недоступен из данной сессии; возможно ограничение sandbox/неработающий сервис |
| Локальные manifests | qwen2.5-coder:3b и qwen3.5:397b-cloud в ~/.ollama/models/manifests/registry.ollama.ai/library | только наличие manifests, не перечень реально обслуживаемых моделей |
| qwen2.5-coder:3b manifest | model layer digest sha256:4a188102020e9c9530b687fd6400f775c45e90a0d7baafe65bd0a36963fbb7ba, заявленный размер 1 929 903 072 bytes | digest прочитан из manifest, не независимо рассчитанный SHA файла весов; модель не выбрана и не запущена |
| Embedding model | доступная модель через API не установлена; в обнаруженных manifests embedding model отсутствует | условие этапа 3 |

Не запускались сервисы, не скачивались веса, не расходовался платный API. Способ доступа к LLM, поддержка русского языка, контекст ≥32000, embedding-модель, наименования/версии и SHA весов выбранной локальной модели ещё должны быть подтверждены до серий. Для ресурсов 8 GB нельзя заявлять пригодность любого LLM по одному названию. Требования выбранной модели к RAM/GPU должны быть сверены с её документацией после выбора.

Команды проверки: `java -version`, `python3 --version`, `/opt/homebrew/bin/python3.11 --version`, `/usr/local/bin/python3.11 --version`, `sw_vers`, `uname -m`, `system_profiler SPHardwareDataType SPDisplaysDataType`, `ollama --version`, `curl -sS --max-time 5 http://localhost:11434/api/tags`, поиск Protégé в двух стандартных каталогах. Прямой `sysctl -n hw.memsize hw.ncpu machdep.cpu.brand_string` запрещён sandbox; сведения CPU/RAM взяты из system_profiler. Серийные номера и UUID компьютера намеренно не записаны.
