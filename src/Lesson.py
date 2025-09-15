class Lesson:
    def __init__(
            self,
            number: int,
            start_time: str,
            end_time: str,
            classroom: str,
            title: str,
            is_remote: bool = False,
            week_kind: int | None = None,
            week_variant: int | None = None
    ) -> None:
        self.number = number
        self.start_time = start_time
        self.end_time = end_time
        self.classroom = classroom
        self.title = title
        self.is_remote = is_remote
        self.week_kind = week_kind
        self.week_variant = week_variant

    def __str__(self):
        return (
            f"{self.number} | {self.start_time} - {self.end_time} | "
            f"{self.classroom:6} | {self.title}"
        )
