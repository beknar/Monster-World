import pygame
from src.settings import MUSIC_TRACKS, SFX_PATHS

class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.sfx_cache = {}
        self.current_music = None
        self.music_volume = 0.5
        self.sfx_volume = 0.6

        # Register a custom event so we know when a track finishes
        self.MUSIC_END_EVENT = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)

        self._load_sfx()

    def _load_sfx(self):
        for name, path in SFX_PATHS.items():
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self.sfx_volume)
                self.sfx_cache[name] = sound
            except Exception:
                pass  # Skip missing sound files

    def play_music(self, track_name: str, loops: int = -1):
        """Play a music track by name. loops=-1 means loop forever."""
        if track_name == self.current_music and pygame.mixer.music.get_busy():
            return
        path = MUSIC_TRACKS.get(track_name)
        if path:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(loops)
                self.current_music = track_name
            except Exception:
                pass

    def stop_music(self):
        pygame.mixer.music.stop()
        self.current_music = None

    def play_sfx(self, sfx_name: str):
        """Play a sound effect by name."""
        sound = self.sfx_cache.get(sfx_name)
        if sound:
            sound.play()

    def set_music_volume(self, volume: float):
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sfx_cache.values():
            sound.set_volume(self.sfx_volume)
