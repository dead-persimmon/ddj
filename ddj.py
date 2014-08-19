from tkinter import *
from tkinter import ttk

root = Tk() # has to be here

class State:
    def __init__(self):
    
        self.default_work_dir = 'C:\\~ Downloads'
        
        self.console_text = StringVar()
        self.work_dir_text = StringVar()
        
        self.work_dir_text.set(self.default_work_dir)
        
        self.special_titles = []
        with open('special_titles.txt', 'r') as file:
            for line in file:
                if line and line[0] == '#':
                    continue
                tokens = line.split('::')
                tokens = [x.strip() for x in tokens]
                if len(tokens) == 1:
                    self.special_titles.append({ 'search_term': tokens[0], 'tidy_title': tokens[0] })
                elif len(tokens) == 2:
                    self.special_titles.append({ 'search_term': tokens[0], 'tidy_title': tokens[1] })
            
        self.files_by_id = {}

    def get_work_dir(self):
        global work_dir_text
        return work_dir_text.get()

    def selected_files(self):
        global tree
        file_ids = set()
        for item_id in tree.selection():
            children_ids = tree.get_children(item_id)
            if children_ids: # it's a group
                file_ids |= set(children_ids)
            else: # it's a single file
                file_ids.add(item_id)
        for file_id in file_ids:
            yield file_id

state = State()

def build_normalize_title():
    import re
    esc = re.escape
    re_underscores = re.compile('_')
    re_dots = re.compile('\.')
    re_extensions = re.compile('|'.join(esc('.') + ext + '$' for ext in ('avi', 'mkv', 'mp4')), re.I)
    re_tags = re.compile('|'.join(esc(br[0]) + '[^' + esc(br[1]) + ']*' + esc(br[1]) for br in ('[]', '()', '{}')))
    re_spaces_greedy = re.compile('\s+')
    
    re_episode_number_variants = [re.compile('(?: - )([0-9]+)(?:v[0-9]+)? '), re.compile(' ep?([0-9]+)(?:v[0-9]+)? ', re.I)]
    re_volume_number_variants = [re.compile('\s*-?\s*vol\.?\s*([0-9]+)', re.I)]
    
    re_solo_hyphens = re.compile(' -+ ')
    re_multiple_bangs = re.compile('!+')
    re_greedy_numbers = re.compile('[0-9]+')
    
    def normalize_number(number_string_mo):
        return str(int(number_string_mo.group(0)))
    
    def normalize_title(title):
        original_title = title
        if title.count('_') >= 2:
            title = re_underscores.sub(' ', title)
        title = re_extensions.sub('', title)
        if title.count('.') >= 2:
            title = re_dots.sub(' ', title)
        title = re_tags.sub('', title)
        title = re_spaces_greedy.sub(' ', title)

        episode_number = None
        for re_episode_number in re_episode_number_variants:
            result = re_episode_number.search(title)
            if result:
                episode_number, = result.groups()
                episode_number = int(episode_number)
                title = re_episode_number.sub(' ', title)
                break
        
        for re_volume_number in re_volume_number_variants:
            title = re_volume_number.sub(' Vol. \\1', title)
        
        title = re_solo_hyphens.sub(' — ', title)
        title = re_multiple_bangs.sub('!', title)
        title = re_greedy_numbers.sub(normalize_number, title)
        title = re_spaces_greedy.sub(' ', title)
        
        title = title.strip()
        return (title or original_title, episode_number)
    return normalize_title

normalize_title = build_normalize_title()

def clear_tree():
    global tree
    for item_id in tree.get_children():
        tree.delete(item_id)

def update_tree():
    global state, tree
    
    groups = {}
    
    work_dir = state.work_dir_text.get()

    import os
    from itertools import product
    
    for entry in os.listdir(work_dir):
        path = os.path.join(work_dir, entry)
        if not os.path.isfile(path):
            continue
        normalized_title, episode_number = normalize_title(entry)
        for special_title, title in product(state.special_titles, [normalized_title.lower()]):
            if special_title['search_term'].lower() in title:
                title = special_title['tidy_title']
                break
        else:
            title = normalized_title
        
        groups.setdefault(title, { 'title': title, 'files': [], 'path': path, 'size': 0, 'episodes': set(), 'episodes_text': str() })
        
        if episode_number:
            groups[title]['episodes'].add(episode_number)
            
        file = { 'name': entry, 'path': path, 'size': os.stat(path).st_size // 1024**2 }
        
        groups[title]['files'].append(file)
        groups[title]['size'] += file['size']
        
    for group in sorted(groups.values(), reverse = True, key = lambda x: x['size']):
        episodes = list(group['episodes'])
        if episodes:
            ranges = []
            index_a = 0
            for index_b, (a, b) in enumerate(zip(episodes, episodes[1:] + [episodes[-1]])):
                if b - a != 1:
                    ranges.append((index_a, index_b))
                    index_a = index_b + 1
            group['episodes_text'] = ' (%s)' % ', '.join(
                '%d~%d' % (episodes[index_a], episodes[index_b])
                if index_b - index_a
                else str(episodes[index_a])
                for index_a, index_b in ranges
            )
        
        group_id = tree.insert('', END, text = group['title'] + group['episodes_text'], values = (len(group['files']), group['size']))
        
        for file in group['files']:
            file_id = tree.insert(group_id, END, text = file['name'], values = (1, file['size']))
            state.files_by_id[file_id] = file

# main window
root.title('Downloads Directory Janitor 0.1')
root.geometry('640x720')
root.config(padx = 8, pady = 8)
root.columnconfigure(0, weight = 1)
root.rowconfigure(1, weight = 1)

# top controls
top_frame = ttk.Frame(root)
top_frame.grid(column = 0, columnspan = 2, row = 0, sticky = (W, E), pady = (0, 8))

refresh_button = ttk.Button(top_frame, text = 'Refresh')
refresh_button.pack(side = RIGHT, padx = (8, 0))

work_dir = ttk.Entry(top_frame)
work_dir.pack(side = RIGHT, fill = X, expand = 1)

ttk.Label(top_frame, text = 'Directory').pack(side = LEFT, padx = (0, 8))

# treeview
tree = ttk.Treeview(root, columns = ('files', 'size'))
tree.grid(column = 0, row = 1, sticky = (W, E, N, S))

tree.column('#0', anchor = W)
tree.column('files', width = 80, anchor = E, stretch = NO)
tree.column('size', width = 80, anchor = E, stretch = NO)

tree.heading('#0', text = 'Group', anchor = W)
tree.heading('files', text = 'Files', anchor = E)
tree.heading('size', text = 'Size (Mb)', anchor = E)

# treeview scrollbar
scrollbar = ttk.Scrollbar(root, orient = 'vertical')
scrollbar.grid(column = 1, row = 1, sticky = (N, S), padx = (2, 0))

# console
console = ttk.Entry(root, state = DISABLED)
console.grid(column = 0, columnspan = 2, row = 2, sticky = (W, E), pady = (8, 0))

# bottom controls
buttons_frame = ttk.Frame(root)
buttons_frame.grid(column = 0, columnspan = 2, row = 3, sticky = (W, E))

delete_button = ttk.Button(buttons_frame, text = 'Delete')
delete_button.pack(side = RIGHT, padx = (8, 0), pady = (8, 0))

# handlers
def on_tree_selection_update(event):
    global state
    state.console_text.set('Selected %d files.' % len(list(state.selected_files())))
def on_refresh_button_click():
    global state, tree
    clear_tree()
    
    work_dir = state.work_dir_text.get()
    
    import os
    if not os.path.isdir(work_dir):
        state.console_text.set('(%s) does not appear to be an existing directory.' % work_dir)
        return None

    update_tree()
def on_delete_button_click():
    import os, stat
    global state
    
    files_counter = 0
    size_counter = 0
    
    for file_id in state.selected_files():
        file = state.files_by_id[file_id]
        try:
            os.chmod(file['path'], stat.S_IWRITE)
            os.remove(file['path'])
        except Exception as exception:
            print(exception)
        else:
            files_counter += 1
            size_counter += file['size']
            
    state.console_text.set('Deleted %d files, %d Mb.' % (files_counter, size_counter))
    on_refresh_button_click()

# bindings
tree.config(yscrollcommand = scrollbar.set)
scrollbar.config(command = tree.yview)

console.config(textvariable = state.console_text)
work_dir.config(textvariable = state.work_dir_text)

tree.bind('<<TreeviewSelect>>', on_tree_selection_update)
refresh_button.config(command = on_refresh_button_click)
delete_button.config(command = on_delete_button_click)

#
on_refresh_button_click()
root.mainloop()
