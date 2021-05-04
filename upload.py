import os
from pathlib import Path
from flo.idea import Idea
from flo.video import Video
from flo.trello import Trello
from flo.channel import Channel
from flo.videoflo import VideoFlo
from flo.mactag import update_tag


# get the thumbnail file
def get_thumbnail(path):
    png_files = list(path.glob('[!.]*.png'))
    num_png = len(png_files)
    if num_png != 1:
        print('FIX: Found {} png files'.format(num_png, path))
        return None
    return str(png_files[0])

# get the video file
def get_video_file(path):
    mov_files = list(path.glob('[!.]*.mov'))
    num_mov = len(mov_files)
    if num_mov != 1:
        print('FIX: Found {} mov files'.format(num_mov, path))
        return None
    video_file = Path(mov_files[0]).name
    return video_file

# loop over directories tagged as ready for upload and check for required files
def get_upload_dict(channel, trello):
    print('Checking videos for {}'.format(channel.name))
    uploadable = trello.get_list('Upload', channel)
    upload_dict = {}

    count = 0
    warn = 0
    for item in uploadable:
        metadata = {
            'title': item['name'],
            'description': item['desc'],
            'scheduled': item['due'],
            'tags': trello.get_tags_from_checklist(item['idChecklists']),
        }

        card_id = item['id']
        path = trello.find_path_for_id(card_id, channel)
        if path is None:
            print('Could not find local path for {}'.format(name))
            continue

        path = Path(path)
        project_name = os.path.basename(path)

        idea = Idea()
        idea.from_project(project_name, channel)
        if not idea.exists():
            print('Directory for {} not found'.format(path))
            return

        print('Checking {}'.format(path))
        count = count + 1

        # video thumbnail
        thumbnail = get_thumbnail(path)
        warn = warn + 1 if thumbnail is None else warn

        # video file
        video_file = get_video_file(path)
        warn = warn + 1 if video_file is None else warn

        video = Video(path, video_file, channel, metadata, thumbnail, idea)
        warn = warn + 1 if not video.check_title() else warn
        warn = warn + 1 if not video.check_description() else warn
        warn = warn + 1 if not video.check_date() else warn
        warn = warn + 1 if not video.check_tags() else warn

        upload_dict[card_id] = video

    if warn == 0 and count > 0:
        return upload_dict
    elif count == 0:
        print('No videos ready for upload')
    else:
        print('{} problem(s) found'.format(warn))
    return {}

# prepare uploads
def do_uploads(upload_dict, trello):
    for card_id, video in upload_dict.items():
        print('Starting upload for {}'.format(video.file))
        video_id = video.upload()
        if video_id is not None:
            update_tag('Backup', video.path)
            trello.move_card(video.idea, 'Scheduled')
            trello.attach_links_to_card(card_id, video_id)

def go():
    flo = VideoFlo()
    args = flo.get_channel_arguments()
    channel = Channel(flo.config, args.channel)

    trello = Trello()
    if not trello.lists_exist(['Upload', 'Scheduled'], channel):
        return

    upload_dict = get_upload_dict(channel, trello)
    if len(upload_dict) > 0:
        do_uploads(upload_dict, trello)

go()