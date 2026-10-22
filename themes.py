"""Theme palettes shared by GTK styling and the notch's painted shoulders."""
THEMES = {
    'dark': {'name': 'Dark', 'description': 'Gelap dan kontras untuk mendengarkan malam hari.',
             'surface': (16 / 255, 17 / 255, 22 / 255, 1), 'lyric_dim': '#9197a6'},
    'light': {'name': 'Light', 'description': 'Terang dengan teks dan kontrol berwarna gelap.',
              'surface': (245 / 255, 246 / 255, 250 / 255, 1), 'lyric_dim': '#697083'},
    'blur': {'name': 'Blur', 'description': 'Transparan agar desktop terlihat. Efek kabur mengikuti dukungan compositor.',
             'surface': (16 / 255, 17 / 255, 22 / 255, .62), 'lyric_dim': '#c3c9d8'},
}


def theme_css(base, theme):
    if theme == 'light':
        replacements = {
            '#101116': '#f5f6fa', '#fafafa': '#242735', '#292b35': '#d7dbe5',
            '#9297a6': '#626a7d', '#91949e': '#626a7d', '#b7bbc8': '#515b70',
            '#20222c': '#ffffff', '#f3f4f9': '#242735', '#373a48': '#d3d8e4',
            '#252833': '#e8ebf3', '#303344': '#dce2f0', '#242936': '#e4e9f6',
            '#171921': '#f5f6fa', '#e9ebf0': '#303749', '#272a36': '#e5e9f2',
            '#4c5060': '#a6afc2', '#34394b': '#dce2f0', '#30212a': '#ffe2e8',
            '#ff4c65': '#cf2646', '#ff7c8f': '#b51d3a', '#252832': '#e3e7f0',
            '#f2f3f5': '#303749', '#0a0b0e': '#ffffff', '#30323a': '#cbd1df',
            '#d8dde8': '#667796', '#757b88': '#657088',
        }
        # One pass avoids replacing a newly substituted color a second time.
        import re
        text = base.decode('utf-8')
        text = re.sub('|'.join(re.escape(key) for key in replacements),
                      lambda match: replacements[match[0]], text)
        return text.encode('utf-8')
    if theme == 'blur':
        return base.replace(b'background: #101116;', b'background: rgba(16, 17, 22, 0.62);').replace(
            b'border: 1px solid #292b35;', b'border: 1px solid rgba(220, 225, 245, 0.20);')
    return base
