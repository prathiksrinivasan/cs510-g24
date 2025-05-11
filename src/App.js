import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { Box, TextField, Button, Paper, Container, CssBaseline, Alert, Card, CardContent, CardMedia, Typography, Grid, IconButton } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1b2838', //from the steam color palette
    },
    background: {
      default: '#171a21',
      paper: '#1b2838',
    },
  },
});

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [error, setError] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedApp, setSelectedApp] = useState(null);
  const [lastQuery, setLastQuery] = useState('');

  const handleSearch = async () => {
    try {
      setError('');
      const response = await axios.post(`${API_BASE_URL}/search`, {
        query: searchQuery
      });
      
      if (response.data.status === 'success') {
        setSearchResults(response.data.results);
      }
    } catch (error) {
      setError('Search failed: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleAppClick = async (appId) => {
    try {
      setError('');
      const response = await axios.post(`${API_BASE_URL}/find`, {
        app_id: appId
      });

      if (response.data.status === 'success') {
        setSelectedApp(response.data.details);
        //add app details to chat
        setMessages(prev => [...prev, {
          text: `Selected: ${response.data.details.name}\nPrice: ${response.data.details.price}\nDescription: ${response.data.details.description}\n\nReview Summary: ${response.data.details.summary}`,
          sender: 'system'
        }]);
      }
    } catch (error) {
      setError('Failed to fetch app details: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleAdditionalReviews = async (query) => {
    try {
      setError('');
      //first request additional reviews
      await axios.post(`${API_BASE_URL}/additional-reviews`, {
        query: query
      });
      
      //regenerate response with the same query
      const response = await axios.post(`${API_BASE_URL}/message`, {
        message: query
      });

      if (response.data.status === 'success') {
        setMessages(prev => [...prev, {
          text: response.data.response,
          review_text: response.data.review_text,
          sender: 'system'
        }]);
      }
    } catch (error) {
      setError('Failed to get additional reviews: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleSendMessage = async () => {
    if (newMessage.trim()) {
      try {
        setError('');
        setLastQuery(newMessage); //store the last query
        setMessages(prev => [...prev, { text: newMessage, sender: 'user' }]);
        
        const response = await axios.post(`${API_BASE_URL}/message`, {
          message: newMessage
        });

        if (response.data.status === 'success') {
          setMessages(prev => [...prev, {
            text: response.data.response,
            review_text: response.data.review_text,
            sender: 'system'
          }]);
        }
        
        setNewMessage('');
      } catch (error) {
        setError('Failed to send message: ' + (error.response?.data?.error || error.message));
      }
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth={false} sx={{ height: '100vh', p: 0 }}>
        {error && (
          <Alert severity="error" sx={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'flex', height: '100%' }}>
          {/* Left side - Search Section */}
          <Paper
            elevation={3}
            sx={{
              width: '25%',
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              backgroundColor: 'background.paper',
              overflow: 'auto'
            }}
          >
            <TextField
              fullWidth
              label="Search"
              variant="outlined"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                endAdornment: (
                  <Button
                    variant="contained"
                    onClick={handleSearch}
                    startIcon={<SearchIcon />}
                  >
                    Search
                  </Button>
                ),
              }}
            />
            
            {/* Search Results */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {searchResults.map((result) => (
                <Card 
                  key={result.id}
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'primary.dark'
                    }
                  }}
                  onClick={() => handleAppClick(result.id)}
                >
                  <CardMedia
                    component="img"
                    height="140"
                    image={result.thumbnail}
                    alt={result.title}
                  />
                  <CardContent>
                    <Typography variant="h6" component="div">
                      {result.title}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Box>
          </Paper>

          {/* Right side - Chat Section */}
          <Paper
            elevation={3}
            sx={{
              width: '75%',
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: 'background.paper',
            }}
          >
            {/* Chat messages area */}
            <Box
              sx={{
                flex: 1,
                overflow: 'auto',
                p: 2,
                display: 'flex',
                flexDirection: 'column',
                gap: 1,
              }}
            >
              {messages.map((message, index) => (
                <React.Fragment key={index}>
                  <Box
                    sx={{
                      alignSelf: message.sender === 'user' ? 'flex-end' : 'flex-start',
                      backgroundColor: message.sender === 'user' ? 'primary.main' : '#66c0f4',
                      color: message.sender === 'user' ? 'white' : '#1b2838',
                      p: 1,
                      borderRadius: 1,
                      maxWidth: '70%',
                      whiteSpace: 'pre-line',
                      position: 'relative'
                    }}
                  >
                    {message.text}
                    {message.sender === 'system' && !message.review_text && (
                      <IconButton
                        size="small"
                        onClick={() => handleAdditionalReviews(lastQuery)}
                        sx={{
                          position: 'absolute',
                          right: -40,
                          top: '50%',
                          transform: 'translateY(-50%)',
                          color: '#66c0f4',
                          '&:hover': {
                            color: '#1999ff'
                          }
                        }}
                        title="Request additional reviews"
                      >
                        <RefreshIcon />
                      </IconButton>
                    )}
                  </Box>
                  {message.sender === 'system' && message.review_text && (
                    <Box
                      sx={{
                        alignSelf: 'flex-start',
                        backgroundColor: '#2a475e',
                        color: '#c7d5e0',
                        p: 2,
                        borderRadius: 1,
                        maxWidth: '70%',
                        mt: 1,
                        border: '1px solid #66c0f4',
                        fontStyle: 'italic'
                      }}
                    >
                      <Typography variant="subtitle2" sx={{ color: '#66c0f4', mb: 1 }}>
                        Most Relevant Review:
                      </Typography>
                      {message.review_text}
                    </Box>
                  )}
                </React.Fragment>
              ))}
            </Box>

            {/* Message input area */}
            <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Type a message..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleSendMessage();
                  }
                }}
                InputProps={{
                  endAdornment: (
                    <Button
                      variant="contained"
                      onClick={handleSendMessage}
                      endIcon={<SendIcon />}
                    >
                      Send
                    </Button>
                  ),
                }}
              />
            </Box>
          </Paper>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App; 