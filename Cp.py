async def get_cpwp_course_content(
    session: aiohttp.ClientSession,
    headers: Dict[str, str],
    Batch_Token: str,
    folder_id: int = 0,
    limit: int = 9999999999,
    retry_count: int = 0,
    parent_path: str = ""
) -> Tuple[List[str], int, int, int]:
    MAX_RETRIES = 3
    fetched_urls: set[str] = set()
    results: List[str] = []
    video_count = 0
    pdf_count = 0
    image_count = 0
    content_tasks: List[Tuple[int, asyncio.Task[str | None]]] = []
    folder_tasks: List[Tuple[int, asyncio.Task[List[str]]]] = []

    try:
        content_api = f'https://api.classplusapp.com/v2/course/preview/content/list/{Batch_Token}'
        params = {'folderId': folder_id, 'limit': limit}

        async with session.get(content_api, params=params, headers=headers) as res:
            res.raise_for_status()
            res_json = await res.json()
            contents: List[Dict[str, Any]] = res_json['data']

            for content in contents:
                # ✅ अगर यह एक फोल्डर है
                if content['contentType'] == 1:
                    folder_name = content['name']
                    new_parent_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
                    folder_task = asyncio.create_task(
                        get_cpwp_course_content(session, headers, Batch_Token, content['id'], retry_count=0, parent_path=new_parent_path)
                    )
                    folder_tasks.append((content['id'], folder_task))
                    continue

                # ✅ अगर यह वीडियो या फ़ाइल है
                name: str = content['name']
                url_val: str | None = content.get('url') or content.get('thumbnailUrl')

                if not url_val:
                    logging.warning(f"No URL found for content: {name}")
                    continue                  
                if "media-cdn.classplusapp.com/tencent/" in url_val:
                    url_val = url_val.rsplit('/', 1)[0] + "/master.m3u8"
                elif "media-cdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                    identifier = url_val.split('/')[-3]
                    url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/{identifier}/master.m3u8'
                elif "tencdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                    identifier = url_val.split('/')[-2]
                    url_val = f'https://media-cdn.classplusapp.com/tencent/{identifier}/master.m3u8'
                elif "4b06bf8d61c41f8310af9b2624459378203740932b456b07fcf817b737fbae27" in url_val and url_val.endswith('.jpeg'):
                    url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/b08bad9ff8d969639b2e43d5769342cc62b510c4345d2f7f153bec53be84fe35/{url_val.split('/')[-1].split('.')[0]}/master.m3u8'
                elif "cpvideocdn.testbook.com" in url_val and url_val.endswith('.png'):
                    match = re.search(r'/streams/([a-f0-9]{24})/', url_val)
                    video_id = match.group(1) if match else url_val.split('/')[-2]
                    url_val = f'https://cpvod.testbook.com/{video_id}/playlist.m3u8'
                elif "media-cdn.classplusapp.com/drm/" in url_val and url_val.endswith('.png'):
                    video_id = url_val.split('/')[-3]
                    url_val = f'https://media-cdn.classplusapp.com/drm/{video_id}/playlist.m3u8'
                elif "https://media-cdn.classplusapp.com" in url_val and ("cc/" in url_val or "lc/" in url_val or "uc/" in url_val or "dy/" in url_val) and url_val.endswith('.png'):
                    url_val = url_val.replace('thumbnail.png', 'master.m3u8')
                elif "https://tb-video.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                    video_id = url_val.split('/')[-1].split('.')[0]
                    url_val = f'https://tb-video.classplusapp.com/{video_id}/master.m3u8'
                elif "cdn-wl-assets.classplus.co" in url_val:
                    base_url = url_val.rsplit('.', 1)[0]
                    url_val = base_url + '.pdf

                if url_val.endswith(("master.m3u8", "playlist.m3u8")) and url_val not in fetched_urls:
                    fetched_urls.add(url_val)
                    headers2 = {'x-access-token': 'your-token-here'}
                    task = asyncio.create_task(process_cpwp_url(url_val, name, parent_path, session, headers2))
                    content_tasks.append((content['id'], task))
                else:
                    fetched_urls.add(url_val)
                    results.append(f"{parent_path}/{name}:{url_val}\n" if parent_path else f"{name}:{url_val}\n")
                    if url_val.endswith('.pdf'):
                        pdf_count += 1
                    else:
                        image_count += 1

    except Exception as e:
        logging.exception(f"Error while fetching folder {folder_id}: {e}")
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(2 ** retry_count)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1, parent_path)
        else:
            return [], 0, 0, 0

    # ✅ Results gather
    content_results = await asyncio.gather(*(task for _, task in content_tasks), return_exceptions=True)
    folder_results = await asyncio.gather(*(task for _, task in folder_tasks), return_exceptions=True)

    for result in content_results:
        if isinstance(result, str):
            results.append(result)
            video_count += 1

    for folder_result in folder_results:
        if isinstance(folder_result, tuple):
            nested_results, nested_video, nested_pdf, nested_image = folder_result
            results.extend(nested_results)
            video_count += nested_video
            pdf_count += nested_pdf
            image_count += nested_image

    return results, video_count, pdf_count, image_count
