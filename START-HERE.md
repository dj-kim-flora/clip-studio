# Edit your videos: start here

You don't need to code or know video terms. Give an AI agent your recording; it does the editing and shows you the result.

## 1. Install (once, about 10 minutes)

Get this folder onto your computer (a Mac), then in Terminal:

```sh
cd clip-studio
bash setup.sh
```

Not comfortable in Terminal? Open the folder in Claude Code, Codex or Cursor and say **"set this up for me"**. The agent
runs the setup and tells you if anything needs you.

## 2. Make something

Open the folder in your agent and say what you have, for example:

> Pull the best clips out of my podcast. It's at ~/Downloads/episode-12.mp4.
> Make a 60-second highlight from this webinar.
> Remove the ums and long pauses from this recording.
> Turn this into Reels, with captions.
> Make a behind-the-scenes reel from this project link: https://...   (it records the page for you, in the background)

You can hand it a file, a folder, or a link (YouTube, Vimeo, Zoom, Loom, Drive, Dropbox).

The agent will:
1. set everything up and read the whole recording;
2. ask up to four quick multiple-choice questions, with a suggested answer for each: what it's for, where people will watch
   it, how much you want, and what it should look like;
3. show you a plan, such as a ranked list of the best moments, and wait for your yes;
4. for a set of clips, make one test clip first so you can approve the look;
5. make the rest and put the files in `deliverables/`, with captions (`.srt`) and a thumbnail for each.

## 3. Your look

Send **brand guidelines** (a PDF, a link, colours, fonts, a logo) or **a video you like the look of**, and the agent
copies the style: colours, type, caption style, end card. With neither, it uses a clean neutral look. You can restyle
any time: "make it warmer", "bigger captions", "use my logo at the end".

## 4. Give feedback in plain words

"Make it shorter." "Punchier." "Start with the pricing question instead." "That part is boring." "Take out the part about
the customer." "Another one just like clip 3." The agent translates; you don't need any video terms.

## What you get

Fast, clear videos in 9:16 (TikTok, Reels, Shorts), 4:5 (feed), 1:1 (square) or 16:9 (YouTube): each one starts on its best
line, cuts the ums and dead air, has captions that light up as words are spoken, evenly loud audio, and your end card.
Music only if you give a track or approve one. If a moment isn't funny, striking or something people would care about, the
agent cuts it.

Works on podcasts, interviews, livestreams, webinars, talks, lectures, tutorials, screen demos, vlogs and events, in
most languages.

## Good to know

- For a link, the agent only looks at the page (it never clicks or edits anything). If the page needs a login, a window opens once and you sign in yourself.
- Your original recording is never changed, uploaded or published. The agent gives you the files; you post them.
- Nothing is spent without a price and your yes. Music, footage and fonts must be ones you may use.
- Fonts, logos and brand files stay on your computer and are not committed to git.
- Something odd? Say so. The agent keeps a log (`EDIT-LOG.md`) and can redo any round.

## For the agent

Read `SKILL.md`, then `skill/references/intake.md`. Run `bash check.sh` first.
