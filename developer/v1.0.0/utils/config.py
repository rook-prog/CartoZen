shape_map = {'Circle': 'o', 'Triangle': '^', 'Square': 's', 'Diamond': 'D'}
page_dims = {'A4': (8.27, 11.69), 'A3': (11.69, 16.54), 'Letter': (8.5, 11)}

def get_page_size(name, orientation):
    w, h = page_dims[name]
    return (w, h) if orientation.lower() == "portrait" else (h, w)
