import { useState, useRef } from 'react';

// API URL (Assumes proxy or CORS)
const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/chat_stream";

export const useAgent = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Namaste! I am the Digital Rishi. Ask me about Life, Strategy, or Dharma.', thoughts: [] }
  ]);
  const [isThinking, setIsThinking] = useState(false);
  const [currentThought, setCurrentThought] = useState("");

  const sendMessage = async (query) => {
    // Add user message
    const userMsg = { role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setIsThinking(true);
    setCurrentThought("Connecting to the Archives...");

    // Create placeholder for assistant response
    const assistantMsgId = Date.now();
    setMessages(prev => [...prev, { 
      id: assistantMsgId, 
      role: 'assistant', 
      content: '', 
      thoughts: [] 
    }]);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query })
      });

      if (!response.body) throw new Error("No stream");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
            console.log("Stream reader done.");
            break;
        }

        const chunk = decoder.decode(value, { stream: true });
        console.log("Received chunk:", chunk);
        buffer += chunk;
        const lines = buffer.split('\n');
        
        // Process complete lines
        buffer = lines.pop(); // Keep incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            console.log("Parsing line:", line);
            const data = JSON.parse(line);
            console.log("Parsed data:", data);
            
            // Handle Plan Events
            if (data.type === 'plan') {
                setMessages(prev => {
                    // Attach plan to the last assistant message
                    const lastMsg = prev[prev.length - 1];
                    if (lastMsg.role === 'assistant') {
                        return prev.map(m => m.id === lastMsg.id ? { ...m, plan: data.steps, planCompletedIndex: data.completed } : m);
                    }
                    return prev;
                });
            }
            if (data.type === 'plan_update') {
                 setMessages(prev => {
                    const lastMsg = prev[prev.length - 1];
                    if (lastMsg.role === 'assistant') {
                        return prev.map(m => m.id === lastMsg.id ? { ...m, planCompletedIndex: data.completed } : m);
                    }
                    return prev;
                });
            }

            if (data.type === 'step_detail') {
                 setMessages(prev => {
                    const lastMsg = prev[prev.length - 1];
                    if (lastMsg.role === 'assistant') {
                        return prev.map(m => {
                            if (m.id !== lastMsg.id) return m;
                            
                            const prevDetails = m.planDetails || {};
                            const stepDetails = prevDetails[data.step_index] || [];
                            
                            // Dedup: don't add if already exists (server might re-emit state)
                            if (stepDetails.includes(data.detail)) return m;

                            // Create a new details array
                            const newDetailsForStep = [...stepDetails, data.detail];
                            
                            return { 
                                ...m, 
                                planDetails: {
                                    ...prevDetails,
                                    [data.step_index]: newDetailsForStep
                                }
                            };
                        });
                    }
                    return prev;
                });
            }
            
            setMessages(prev => prev.map(msg => {
              if (msg.id !== assistantMsgId) return msg;

              if (data.type === 'thought') {
                return { 
                  ...msg, 
                  thoughts: [...msg.thoughts, data.content] 
                };
              } else if (data.type === 'answer') {
                 // Append to content (usually streaming tokens, but our agent sends full chunks)
                 // Wait, our server sends: {"type": "answer", "content": "Full text"}?
                 // Let's check server.py.
                 // "yield json.dumps(... content: last_msg.content)"
                 // If run_agent_cli prints final answer at END, then here we might get chunks or full updates.
                 // agent.stream(stream_mode="values") returns the FULL state at each step?
                 // Yes. So data.content is the ACCUMULATED content?
                 // No, server logic:
                 // if "messages" in event: last_msg = ...
                 // It yields the content of the LAST message.
                 // If it's the SAME message growing, it yields full text each time?
                 // LangGraph "values" stream: yields the whole state.
                 // So `last_msg.content` is likely the COMPLETE content so far.
                 // So we should REPLACE content, not append.
                 return { ...msg, content: data.content };
              }
              return msg;
            }));

            if (data.type === 'thought') {
               setCurrentThought(data.content);
            }

          } catch (e) {
            console.error("JSON Parse Error", e);
          }
        }
      }

    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'error', content: "Connection interrupted." }]);
    } finally {
      setIsThinking(false);
      setCurrentThought("");
    }
  };

  return { messages, setMessages, sendMessage, isThinking, currentThought };
};
