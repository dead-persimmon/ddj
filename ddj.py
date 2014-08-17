from tkinter import *
from tkinter import ttk

WORK_DIR = 'C:\\~ Downloads'
SPECIAL_TITLES = []

GROUP_TO_FILE_ID = {}
FILE_TO_GROUP_ID = {}

SELECTED_GROUPS = None
SELECTED_FILES = None

with open('special_titles.txt', 'r') as file:
    for line in file:
        if line and line[0] == '#': continue
        tokens = line.split('::')
        tokens = [x.strip() for x in tokens]
        if len(tokens) == 1:
            SPECIAL_TITLES.append({ 'search_term': tokens[0], 'tidy_title': tokens[0] })
        elif len(tokens) == 2:
            SPECIAL_TITLES.append({ 'search_term': tokens[0], 'tidy_title': tokens[1] })
        else:
            continue

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

# main window
root = Tk()
root.title('Downloads Directory Janitor 0.1')
root.geometry('640x720')
root.config(padx = 8, pady = 8)
root.columnconfigure(0, weight = 1)
root.rowconfigure(1, weight = 1)

# top controls
top_frame = ttk.Frame(root)
top_frame.grid(column = 0, columnspan = 2, row = 0, sticky = (W, E), pady = (0, 8))

def refresh_button_click():
    global work_dir_text, console_text, tree
    
    work_dir = work_dir_text.get()
    
    import os
    if not os.path.isdir(work_dir):
        console_text.set('(%s) does not appear to be an existing directory.' % work_dir)
        return None

    populate_tree(tree)

refresh_button = ttk.Button(top_frame, text = 'Refresh')
refresh_button.pack(side = RIGHT, padx = (8, 0))
refresh_button.config(command = refresh_button_click)

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
def delete_button_click():
    def delete_file(group_id, file_id):
        import os, stat
        global GROUP_TO_FILE_ID, tree, console_text
        file = GROUP_TO_FILE_ID[group_id][file_id]
        try:
            #console_text.set('Attempting to delete (%s).' % file['path'])
            os.chmod(file['path'], stat.S_IWRITE)
            os.remove(file['path'])
            return (1, file['size'])
        except Exception as e:
            print(e)
            return (0, 0)
    
    global tree, SELECTED_FILES, SELECTED_GROUPS, GROUP_TO_FILE_ID, console_text
    
    files_counter = 0
    size_counter = 0
    
    for file_id in SELECTED_FILES:
        files, size = delete_file(tree.parent(file_id), file_id)
        files_counter += files
        size_counter += size
        #tree.delete(file_id)
    for group_id in SELECTED_GROUPS:
        for file_id in tree.get_children(group_id):
            files, size = delete_file(group_id, file_id)
            files_counter += files
            size_counter += size
            #tree.delete(file_id)
        tree.delete(group_id)
    console_text.set('Deleted %d files, %d Mb.' % (files_counter, size_counter))
    refresh_button_click()
    
delete_button.config(command = delete_button_click)

#button2 = ttk.Button(buttons_frame, text = 'B2').pack(side = RIGHT, padx = (8, 0), pady = (8, 0))

# vars
console_text = StringVar()

work_dir_text = StringVar()
work_dir_text.set(WORK_DIR)

# bindings
tree.config(yscrollcommand = scrollbar.set)
scrollbar.config(command = tree.yview)

console.config(textvariable = console_text)

work_dir.config(textvariable = work_dir_text)

def populate_tree(tree):
    import os
    from itertools import product

    global GROUP_TO_FILE_ID, FILE_TO_GROUP_ID
    GROUP_TO_FILE_ID.clear()
    FILE_TO_GROUP_ID.clear()

    groups = {}
    
    for item_id in tree.get_children():
        tree.delete(item_id)

    global work_dir_text
    work_dir = work_dir_text.get()

    for entry in os.listdir(work_dir):
        path = os.path.join(work_dir, entry)
        if not os.path.isfile(path):
            continue
        
        title, episode_number = normalize_title(entry)
        for special_title, title in product(SPECIAL_TITLES, [title]):
            if special_title['search_term'].lower() in title.lower():
                title = special_title['tidy_title']
                break
        
        if title not in groups.keys():
            groups[title] = { 'title': title, 'files': [], 'path': path, 'size': 0, 'episodes': set() }
            
        if episode_number:
            groups[title]['episodes'].add(episode_number)
            
        file = { 'name': entry, 'path': path, 'size': os.stat(path).st_size // 1024**2 }
        
        groups[title]['files'].append(file)
        groups[title]['size'] += file['size']
        
    for group in sorted(groups.values(), reverse = True, key = lambda x: x['size']):
        text_tag = group['title']
        episodes = list(group['episodes'])
        if episodes:
            ranges = []
            index_a = 0
            for index_b, (a, b) in enumerate(zip(episodes, episodes[1:] + [episodes[-1]])):
                if b - a != 1:
                    ranges.append((index_a, index_b))
                    index_a = index_b + 1
            text_tag += ' (%s)' % ', '.join('%d~%d' % (episodes[index_a], episodes[index_b]) if index_b - index_a else str(episodes[index_a]) for index_a, index_b in ranges)
        
        group_id = tree.insert('', END, text = text_tag, values = (len(group['files']), group['size']))
        GROUP_TO_FILE_ID[group_id] = {}
        
        for file in group['files']:
            file_id = tree.insert(group_id, END, text = file['name'], values = (1, file['size']))
            GROUP_TO_FILE_ID[group_id][file_id] = file
            FILE_TO_GROUP_ID[file_id] = group_id

def on_tree_selection_update(event):
    global SELECTED_GROUPS, SELECTED_FILES
    SELECTED_GROUPS, SELECTED_FILES = [], []
    for item_id in tree.selection():
        if item_id in GROUP_TO_FILE_ID.keys():
            SELECTED_GROUPS.append(item_id)
        elif item_id in FILE_TO_GROUP_ID.keys():
            SELECTED_FILES.append(item_id)
    SELECTED_FILES = [sf for sf in SELECTED_FILES if FILE_TO_GROUP_ID[sf] not in SELECTED_GROUPS]
    console_text.set('Selected %d groups and %d individual files.' % (len(SELECTED_GROUPS), len(SELECTED_FILES)))
    
tree.bind('<<TreeviewSelect>>', on_tree_selection_update)

#
refresh_button_click()
root.mainloop()
