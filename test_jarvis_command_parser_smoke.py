from core.jarvis_command_parser import JarvisCommandParser
from shared.jarvis_enums import JarvisCommandType


def main() -> None:
    parser = JarvisCommandParser()

    system_command = parser.parse("Wie ist der Systemstatus?")
    assert system_command.command_type == JarvisCommandType.SYSTEM_STATUS

    weak_platform_command = parser.parse("Welche Plattform ist schwach?")
    assert weak_platform_command.command_type == JarvisCommandType.WEAK_PLATFORMS

    unknown_command = parser.parse("mach irgendwas futuristisches")
    assert unknown_command.command_type == JarvisCommandType.UNKNOWN

    print("JARVIS COMMAND PARSER SMOKE TEST PASSED")
    print(
        {
            "system_status": system_command.to_dict(),
            "weak_platforms": weak_platform_command.to_dict(),
            "unknown": unknown_command.to_dict(),
        }
    )


if __name__ == "__main__":
    main()