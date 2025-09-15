from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from Lesson import Lesson


class Parser:
    def __init__(self, url: str = 'https://miet.ru/schedule'):
        self.firefox_options = webdriver.FirefoxOptions()
        self.firefox_options.headless = True
        self.driver = webdriver.Firefox(options=self.firefox_options)
        self.url = url
        self.driver.get(url)
        self.session_id = self.get_session_id()
        self.groups_names = self.get_groups_names()
        self.group_chosen = False
        self.table_body = None
        self.table_header = None
        self.semester = None
        self.semester_title = None
        self.week_name = None
        self.week_type = None
        self.days_names = None
        self.days_types = None
        self.schedule_type = None
        self.group_name = None
        self.lesson_entries = None
        self.cell_text = None
        self.times = None
        self.days_schedule = {
            'Понедельник': [],
            'Вторник': [],
            'Среда': [],
            'Четверг': [],
            'Пятница': [],
            'Суббота': [],
        }

    def _wait_for_schedule(self, timeout: int = 30) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.schedule table.data tbody')
                )
            )
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.schedule table.data tbody tr')
                )
            )
            return True
        except Exception:
            return False

    def _make_soup(self, html: str) -> BeautifulSoup:
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            return BeautifulSoup(html, "html.parser")

    def __del__(self):
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
        except Exception:
            pass

    def get_group_id(self, group_name: str) -> int:
        if group_name in self.groups_names:
            return self.groups_names.index(group_name) + 1
        else:
            return -1

    def get_groups_names(self) -> tuple:
        src = self.driver.page_source
        soup = self._make_soup(src)
        groups = soup.find(class_='group')
        return tuple([
            i.string for i in groups.find_all('option') if i.string is not None
        ])

    def choose_week_schedule(
            self,
            xpath: str = '/html/body/main/div[2]/div[2]/div[1]/div[2]/span[1]'
    ) -> bool:
        return self.click_button(xpath)

    def choose_day_schedule(
            self,
            xpath: str = '/html/body/main/div[2]/div[2]/div[1]/div[2]/span[2]'
    ) -> bool:
        return self.click_button(xpath)

    def click_dropdown_menu(
            self,
            xpath: str = '/html/body/main/div[2]/div[2]/div[1]/div[1]/span'
    ) -> bool:
        return self.click_button(xpath)

    def choose_group(self, group_name) -> bool:
        group_id = self.get_group_id(group_name)
        if group_id == -1:
            print(f"Couldn't find group {group_name}")
            return False
        xpath = f"//*[@id='{self.session_id}']/li[{group_id}]"
        status = self.click_button(xpath)
        self.group_chosen = status
        if not status:
            print(f"Could find group {group_name} with group_id = {group_id}")
        else:
            self.group_name = group_name
            self._wait_for_schedule(timeout=40)
        return status

    def get_session_id(self) -> int:
        self.click_dropdown_menu()
        ids = self.driver.find_elements(By.XPATH, '//*[@id]')
        return ids[-1].get_attribute('id')

    def click_button(self, xpath: str) -> bool:
        try:
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            ).click()
            return True
        except NoSuchElementException:
            print(f"Couldn't find button with xpath = {xpath}")
            return False

    def get_table(self, period: str = 'today') -> bool:
        if self.group_chosen:
            self.click_dropdown_menu()
            if period == 'today':
                self.choose_day_schedule()
                self.schedule_type = 'today'
            if period == 'week':
                self.choose_week_schedule()
                self.schedule_type = 'week'
            if not self._wait_for_schedule(timeout=40):
                return False
            soup = self._make_soup(self.driver.page_source)
            schedule_div = soup.find('div', class_='schedule')
            table = None
            if schedule_div is not None:
                table = schedule_div.find('table', class_='data')
            if table is not None:
                self.table_header = table.find('thead')
                self.table_body = table.find('tbody')
                self.semester = soup.find(class_='semestr')
                if self.table_body is not None:
                    has_rows = self.table_body.find('tr') is not None
                    return has_rows
            return False
        else:
            print('Must choose group before getting table.')
            return False

    def parse_semester(self) -> None:
        if self.semester is None:
            self.semester_title = ''
            self.week_name = ''
            self.week_type = None
            return
        text = self.semester.get_text(strip=True)
        if '.' in text:
            self.semester_title, self.week_name = text.split('.', 1)
        else:
            self.semester_title, self.week_name = text, ''
        if self.week_name.startswith('1-й ч'):
            self.week_type = 0
        elif self.week_name.startswith('1-й з'):
            self.week_type = 1
        elif self.week_name.startswith('2-й ч'):
            self.week_type = 2
        elif self.week_name.startswith('2-й з'):
            self.week_type = 3
        else:
            self.week_type = None
        if len(self.semester_title) >= 2:
            self.semester_title = self.semester_title[:-2]

    def parse_table_header(self) -> None:
        if self.table_header is not None:
            if self.schedule_type == 'today':
                self.days_names = []
                for th in self.table_header.find_all('th', class_='day'):
                    th_date, th_day_name = th.text.split(' ')
                    th_day_name = th_day_name[1:-1]
                    self.days_names.append((th_day_name, th_date))
            elif self.schedule_type == 'week':
                self.days_names = [
                    ('Понедельник',),
                    ('Вторник',),
                    ('Среда',),
                    ('Четверг',),
                    ('Пятница',),
                    ('Суббота',),
                ]

    def parse_table_body(self) -> None:
        if self.table_body is None:
            raise ValueError(
                'Table body is not loaded. Call get_table() first and ensure '
                'it returns True.'
            )
        tr_tags = []
        self.cell_text = []
        self.times = []
        for tr in self.table_body.find_all('tr'):
            tr_tags.append(tr)
            time_div = tr.find('th', class_='time').find('div')
            div_time = (
                str(time_div)
                .replace('<div>', '')
                .replace('<hr/>', '|')
                .replace('<br/>', '|')
                .replace('</div>', '|')
            )
            div_items = div_time.split('|')
            if len(div_items) == 6:
                del div_items[3:5]
            self.times.append(div_time)

            if self.schedule_type == 'today':
                div_cell = tr.find('div', class_='cell')
                self.cell_text.append(div_cell.text)
                classroom = ''
                title = ''
                if div_cell.text != '':
                    parts = div_cell.text.split(' | ')
                    classroom = parts[0] if len(parts) > 0 else ''
                    title = parts[1] if len(parts) > 1 else ''
                self.days_schedule[self.days_names[0][0]].append(
                    Lesson(
                        number=int(div_items[0][0]),
                        start_time=div_items[1],
                        end_time=div_items[2],
                        classroom=classroom,
                        title=title
                    )
                )
            elif self.schedule_type == 'week':
                tds = tr.find_all('td')
                day_cells = [td.find('div', class_='cell') for td in tds]
                for idx, div_cell in enumerate(day_cells):
                    if idx >= len(self.days_names):
                        break
                    cell_texts = []
                    kinds = []
                    if div_cell is not None:
                        for block in div_cell.find_all('div'):
                            cls = block.get('class') or []
                            week_kind = None
                            week_variant = None
                            for c in cls:
                                if (
                                    c.startswith('type-')
                                    and c not in (
                                        'type-num-0',
                                        'type-num-1',
                                        'type-num-2',
                                    )
                                ):
                                    try:
                                        kind_num = int(c.split('-')[1])
                                        if kind_num in (0, 1, 2):
                                            week_kind = kind_num
                                    except Exception:
                                        pass
                                if c.startswith('type-num-'):
                                    try:
                                        week_variant = int(c.split('-')[-1])
                                    except Exception:
                                        pass
                            text_div = block.find('div', class_='text')
                            if text_div is not None:
                                txt = text_div.get_text(strip=True)
                                if txt:
                                    cell_texts.append(txt)
                                    kinds.append((week_kind, week_variant))
                    if not cell_texts:
                        self.days_schedule[self.days_names[idx][0]].append(
                            Lesson(
                                number=int(div_items[0][0]),
                                start_time=div_items[1],
                                end_time=div_items[2],
                                classroom='',
                                title='',
                                week_kind=None,
                                week_variant=None
                            )
                        )
                    else:
                        for i_raw, raw in enumerate(cell_texts):
                            parts = raw.split(' | ', 1)
                            classroom = parts[0] if len(parts) > 0 else ''
                            title = parts[1] if len(parts) > 1 else ''
                            wk, wv = (None, None)
                            if i_raw < len(kinds):
                                wk, wv = kinds[i_raw]
                            self.days_schedule[self.days_names[idx][0]].append(
                                Lesson(
                                    number=int(div_items[0][0]),
                                    start_time=div_items[1],
                                    end_time=div_items[2],
                                    classroom=classroom,
                                    title=title,
                                    week_kind=wk,
                                    week_variant=wv
                                )
                            )

    def form_report(self) -> str:
        schedule_string = ''
        for i in range(7):
            schedule_string = '{}\n{}'.format(
                schedule_string,
                self.days_schedule[self.days_names[0][0]][i]
            )
        report = '{}\n{}, {}\n{}\n\nГруппа: {}\n{}'.format(
            self.semester_title,
            self.days_names[0][0],
            self.days_names[0][1],
            self.week_name,
            self.group_name,
            schedule_string
        )
        return report

    def _russian_weekday_by_index(self, idx: int) -> str:
        mapping = {
            0: 'Понедельник',
            1: 'Вторник',
            2: 'Среда',
            3: 'Четверг',
            4: 'Пятница',
            5: 'Суббота',
            6: 'Воскресенье',
        }
        return mapping.get(idx, '')

    def _weekday_index_by_russian(self, name: str) -> int:
        mapping = {
            'Понедельник': 0,
            'Вторник': 1,
            'Среда': 2,
            'Четверг': 3,
            'Пятница': 4,
            'Суббота': 5,
            'Воскресенье': 6,
        }
        return mapping.get(name, -1)

    def _parse_hhmm(self, hhmm: str) -> tuple:
        parts = hhmm.strip().split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return hour, minute

    def _format_dt(self, dt: datetime) -> str:
        return dt.strftime('%Y%m%dT%H%M%S')

    def save_semester_ics(
            self,
            start: date,
            end: date,
            filename: str = 'schedule_semester.ics'
    ) -> None:
        lines = []
        lines.append('BEGIN:VCALENDAR')
        lines.append('VERSION:2.0')
        lines.append('PRODID:-//miet-schedule//EN')

        current = start
        while current <= end:
            weekday_idx = current.weekday()
            if weekday_idx <= 5:
                day_name = self._russian_weekday_by_index(weekday_idx)
                lessons = self.days_schedule.get(day_name, [])
                for lesson in lessons:
                    # фильтр пустых и «Военная подготовка»
                    if (
                        (lesson.title == '' and lesson.classroom == '') or
                        ('Военная подготовка' in lesson.title)
                    ):
                        continue
                    # 4-недельный цикл от даты start
                    week_index_from_start = ((current - start).days) // 7
                    mod = week_index_from_start % 4
                    week_kind = lesson.week_kind
                    week_variant = lesson.week_variant
                    should_render = False
                    if week_kind in (None, 0):
                        # общий — на всех неделях
                        should_render = True
                    elif week_kind == 1:  # числитель
                        if week_variant in (None, 0):
                            should_render = mod in (0, 2)
                        elif week_variant == 1:
                            should_render = (mod == 0)
                        elif week_variant == 2:
                            should_render = (mod == 2)
                    elif week_kind == 2:  # знаменатель
                        if week_variant in (None, 0):
                            should_render = mod in (1, 3)
                        elif week_variant == 1:
                            should_render = (mod == 1)
                        elif week_variant == 2:
                            should_render = (mod == 3)
                    if not should_render:
                        continue
                    sh, sm = self._parse_hhmm(lesson.start_time)
                    eh, em = self._parse_hhmm(lesson.end_time)
                    dt_start = datetime(
                        current.year, current.month, current.day, sh, sm, 0
                    )
                    dt_end = datetime(
                        current.year, current.month, current.day, eh, em, 0
                    )
                    uid = (
                        f"{self.group_name}-{current.isoformat()}-"
                        f"{lesson.number}-{lesson.title}"
                    ).replace(' ', '-')
                    lines.append('BEGIN:VEVENT')
                    lines.append(f'UID:{uid}')
                    lines.append(
                        f'DTSTAMP:{self._format_dt(datetime.utcnow())}'
                    )
                    lines.append(f'DTSTART:{self._format_dt(dt_start)}')
                    lines.append(f'DTEND:{self._format_dt(dt_end)}')
                    summary = lesson.title if lesson.title else 'Занятие'
                    lines.append(f'SUMMARY:{summary}')
                    if lesson.classroom:
                        lines.append(f'LOCATION:{lesson.classroom}')
                    if self.group_name:
                        lines.append(
                            f'DESCRIPTION:Группа {self.group_name}'
                        )
                    lines.append('END:VEVENT')
            current += timedelta(days=1)

        lines.append('END:VCALENDAR')

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


if __name__ == '__main__':
    parser = Parser()
    try:
        parser.choose_group('П-32')
        ok = parser.get_table('week')
        if not ok:
            print(
                'Не удалось загрузить таблицу расписания. '
                'Проверьте доступность сайта/группы и повторите.'
            )
            raise SystemExit(1)
        try:
            parser.parse_semester()
            parser.parse_table_header()
            parser.parse_table_body()
            year = date.today().year
            start_sem = date(year, 9, 1)
            end_sem = date(year, 12, 31)
            parser.save_semester_ics(
                start_sem,
                end_sem,
                filename='schedule_semester.ics'
            )
            print('Файл schedule_semester.ics создан.')
        except Exception as e:
            print(f'Ошибка при разборе/генерации: {e}')
            raise SystemExit(1)
    finally:
        try:
            parser.driver.quit()
        except Exception:
            pass
