#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>
#include <stdlib.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show) {
    wchar_t folder[32768];
    DWORD length = GetModuleFileNameW(NULL, folder, 32768);
    if (!length || length >= 32768) return 1;
    wchar_t *slash = wcsrchr(folder, L'\\');
    if (!slash) return 1;
    *slash = 0;
    size_t capacity = 2 * wcslen(folder) + wcslen(arguments) + 256;
    wchar_t *command = calloc(capacity, sizeof(wchar_t));
    if (!command) return 1;
    swprintf(command, capacity, L"\"%ls\\runtime\\bin\\pythonw.exe\" \"%ls\\app\\bootstrap.py\" %ls",
             folder, folder, arguments);
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    BOOL started = CreateProcessW(NULL, command, NULL, NULL, FALSE,
                                  CREATE_UNICODE_ENVIRONMENT, NULL, folder, &startup, &process);
    free(command);
    if (!started) {
        MessageBoxW(NULL, L"Tidak dapat menjalankan runtime. Ekstrak seluruh ZIP terlebih dahulu.",
                    L"Notch Music", MB_OK | MB_ICONERROR);
        return 1;
    }
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD result = 1;
    GetExitCodeProcess(process.hProcess, &result);
    CloseHandle(process.hProcess);
    return (int)result;
}
