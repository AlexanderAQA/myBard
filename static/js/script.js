document.addEventListener('DOMContentLoaded', function() {
    const foldersDiv = document.getElementById('folders');
    const filesDiv = document.getElementById('files');
    const randomWaveButton = document.getElementById('randomWaveButton');
    const audioPlayer = document.getElementById('audioPlayer');
    const randomButton = document.getElementById('randomButton');
    const nowPlayingDiv = document.getElementById('nowPlaying');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');

    const playPauseButton = document.getElementById('playPauseButton');
    const muteButton = document.getElementById('muteButton');
    const seekBar = document.getElementById('seekBar');
    const volumeBar = document.getElementById('volumeBar');
    const currentTimeDisplay = document.getElementById('currentTime');
    const durationDisplay = document.getElementById('duration');
    const trackTitle = document.getElementById('trackTitle');
    const trackArtist = document.getElementById('trackArtist');

    const lowGainSlider = document.getElementById('lowGain');
    const midGainSlider = document.getElementById('midGain');
    const highGainSlider = document.getElementById('highGain');
    const resetEQButton = document.getElementById('resetEQButton');

    let audioContext;
    let currentPath = '';
    let playlist = [];
    let currentSongIndex = 0;

    let lowGainNode, midGainNode, highGainNode;

    function generateRandomPlaylist(songs) {
        const playlist = [];
        let totalDuration = 0;

        while (totalDuration < 7200 && songs.length > 0) {
            const randomIndex = Math.floor(Math.random() * songs.length);
            const selectedSong = songs[randomIndex];
            if (totalDuration + selectedSong.duration <= 7200) {
                playlist.push(selectedSong);
                totalDuration += selectedSong.duration;
                songs.splice(randomIndex, 1);
            } else {
                break;
            }
        }

        return playlist;
    }

    function loadPlaylist(newPlaylist) {
        playlist = newPlaylist;
        currentSongIndex = 0;
        updateNowPlaying();
        playCurrentSong();
    }

    function playCurrentSong() {
        if (playlist.length === 0) return;
        const song = playlist[currentSongIndex];
        audioPlayer.src = `/api/song/${encodeURIComponent(song.path)}`;
        audioPlayer.play();
        updateNowPlaying();
    }

    function updateNowPlaying() {
        nowPlayingDiv.innerHTML = 'Playlist:<br>';
        playlist.forEach((song, index) => {
            const songDiv = document.createElement('div');
            songDiv.textContent = song.path.split('/').pop();
            if (index === currentSongIndex) {
                songDiv.style.color = 'red';
            }
            nowPlayingDiv.appendChild(songDiv);
        });
        updateTrackInfo();
    }

    function updateTrackInfo() {
        const song = playlist[currentSongIndex];
        if (song) {
            trackTitle.textContent = song.path.split('/').pop();
            trackArtist.textContent = 'Unknown Artist';  // Update this with actual artist info if available
        }
    }

    function fetchFiles(path = '') {
        const apiPath = path ? `/api/music/${encodeURIComponent(path)}` : '/api/music';
        return fetch(apiPath)
            .then(response => response.json())
            .then(data => {
                if (!data || typeof data !== 'object') {
                    console.error('Invalid data format:', data);
                    return [];
                }

                if (Array.isArray(data)) {
                    const promises = data.map(folder => fetchFiles(path ? `${path}/${folder}` : folder));
                    return Promise.all(promises).then(results => results.flat());
                }

                const { directories = [], files = [] } = data;
                const filePromises = directories.map(directory => {
                    const directoryPath = path ? `${path}/${directory}` : directory;
                    return fetchFiles(directoryPath);
                });

                const flacFiles = files.filter(file => file.endsWith('.flac')).map(file => ({
                    path: path ? `${path}/${file}` : file,
                    duration: Math.floor(Math.random() * 300 + 180)
                }));

                return Promise.all(filePromises).then(nestedFiles => flacFiles.concat(...nestedFiles));
            })
            .catch(error => {
                console.error('Error fetching files:', error);
                return [];
            });
    }

    randomWaveButton.addEventListener('click', function() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.AudioContext)();
            setupEqualizer();
        } else if (audioContext.state === 'suspended') {
            audioContext.resume();
        }

        fetchFiles('')
            .then(files => {
                const newPlaylist = generateRandomPlaylist(files);
                loadPlaylist(newPlaylist);
            })
            .catch(error => {
                console.error('Error fetching music data:', error);
            });
    });

    function loadFolders(path = '') {
        const apiPath = path ? `/api/music/${encodeURIComponent(path)}` : '/api/music';
        fetch(apiPath)
            .then(response => response.json())
            .then(data => {
                if (!data || typeof data !== 'object') {
                    console.error('Invalid data format:', data);
                    return;
                }

                foldersDiv.innerHTML = '';
                filesDiv.innerHTML = '';

                if (path === '') {
                    data.directories.forEach(folder => {
                        const folderButton = document.createElement('button');
                        folderButton.textContent = folder;
                        folderButton.onclick = () => {
                            currentPath = folder;
                            loadFolders(folder);
                        };
                        foldersDiv.appendChild(folderButton);
                    });
                } else {
                    const backButton = document.createElement('button');
                    backButton.textContent = 'Back';
                    backButton.onclick = () => {
                        const lastIndex = currentPath.lastIndexOf('/');
                        currentPath = currentPath.substring(0, lastIndex);
                        loadFolders(currentPath);
                    };
                    foldersDiv.appendChild(backButton);

                    data.directories.forEach(folder => {
                        const folderButton = document.createElement('button');
                        folderButton.textContent = folder;
                        folderButton.onclick = () => {
                            currentPath += `/${folder}`;
                            loadFolders(currentPath);
                        };
                        foldersDiv.appendChild(folderButton);
                    });

                    data.files.forEach(file => {
                        const fileButton = document.createElement('button');
                        fileButton.textContent = file;
                        fileButton.onclick = () => {
                            const filePath = `${currentPath}/${file}`;
                            audioPlayer.src = `/api/song/${encodeURIComponent(filePath)}`;
                            audioPlayer.play();
                            nowPlayingDiv.textContent = `Now Playing: ${file}`;
                        };
                        filesDiv.appendChild(fileButton);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching folders:', error);
            });
    }

    randomButton.onclick = () => {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.AudioContext)();
            setupEqualizer();
        } else if (audioContext.state === 'suspended') {
            audioContext.resume();
        }

        fetch('/api/random')
            .then(response => response.json())
            .then(data => {
                const filePath = data.file;
                audioPlayer.src = `/api/song/${encodeURIComponent(filePath)}`;
                audioPlayer.play();
                nowPlayingDiv.textContent = `Now Playing: ${filePath.split('/').pop()}`;
                updateTrackInfo();
            })
            .catch(error => {
                console.error('Error fetching random song:', error);
            });
    };

    audioPlayer.oncanplay = () => {
        audioPlayer.play();
    };

    audioPlayer.onerror = (e) => {
        console.error('Error playing audio', e);
    };

    audioPlayer.onended = () => {
        if (currentSongIndex < playlist.length - 1) {
            currentSongIndex++;
            playCurrentSong();
        }
    };

    prevButton.onclick = () => {
        if (currentSongIndex > 0) {
            currentSongIndex--;
            playCurrentSong();
        }
    };

    nextButton.onclick = () => {
        if (currentSongIndex < playlist.length - 1) {
            currentSongIndex++;
            playCurrentSong();
        }
    };

    function setupEqualizer() {
        const gainValues = [lowGainSlider, midGainSlider, highGainSlider];

        // Create the audio context and connect nodes
        audioContext = new (window.AudioContext);
        const source = audioContext.createMediaElementSource(audioPlayer);

        lowGainNode = audioContext.createBiquadFilter();
        lowGainNode.type = 'lowshelf';
        lowGainNode.frequency.value = 320;

        midGainNode = audioContext.createBiquadFilter();
        midGainNode.type = 'peaking';
        midGainNode.frequency.value = 1000;

        highGainNode = audioContext.createBiquadFilter();
        highGainNode.type = 'highshelf';
        highGainNode.frequency.value = 3200;

        source.connect(lowGainNode);
        lowGainNode.connect(midGainNode);
        midGainNode.connect(highGainNode);
        highGainNode.connect(audioContext.destination);

        // Update gain values based on slider inputs
        gainValues.forEach((slider, index) => {
            slider.addEventListener('input', () => {
                const value = parseFloat(slider.value);
                if (index === 0) {
                    lowGainNode.gain.value = value;
                } else if (index === 1) {
                    midGainNode.gain.value = value;
                } else if (index === 2) {
                    highGainNode.gain.value = value;
                }
            });
        });
    }

    // Reset EQ settings
    resetEQButton.addEventListener('click', () => {
        lowGainSlider.value = 0;
        midGainSlider.value = 0;
        highGainSlider.value = 0;
        lowGainNode.gain.value = 0;
        midGainNode.gain.value = 0;
        highGainNode.gain.value = 0;
    });

    // Initialize equalizer on page load
    if (!audioContext) {
        setupEqualizer();
    }

    // Custom controls functionality
    playPauseButton.addEventListener('click', function() {
        if (audioPlayer.paused) {
            audioPlayer.play();
            playPauseButton.innerHTML = '<i class="fas fa-pause"></i>';
        } else {
            audioPlayer.pause();
            playPauseButton.innerHTML = '<i class="fas fa-play"></i>';
        }
    });

    muteButton.addEventListener('click', function() {
        audioPlayer.muted = !audioPlayer.muted;
        muteButton.innerHTML = audioPlayer.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
    });

    seekBar.addEventListener('input', function() {
        const seekTime = audioPlayer.duration * (seekBar.value / 100);
        audioPlayer.currentTime = seekTime;
    });

    volumeBar.addEventListener('input', function() {
        audioPlayer.volume = volumeBar.value;
    });

    audioPlayer.addEventListener('timeupdate', function() {
        const value = (100 / audioPlayer.duration) * audioPlayer.currentTime;
        seekBar.value = value;
        currentTimeDisplay.textContent = formatTime(audioPlayer.currentTime);
        durationDisplay.textContent = formatTime(audioPlayer.duration);
    });

    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        seconds = Math.floor(seconds % 60);
        return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
    }

    loadFolders();
});
