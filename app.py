import streamlit as st
import requests
import json
import random
from typing import List, Dict, Optional, TypedDict, Literal
from dataclasses import dataclass, field
import time
import json
from enum import Enum

class RelationshipLevel(Enum):
    HOSTILE = -2
    UNFRIENDLY = -1
    NEUTRAL = 0
    FRIENDLY = 1
    TRUSTED = 2
    ALLY = 3

@dataclass
class Character:
    name: str
    description: str
    relationship: RelationshipLevel = RelationshipLevel.NEUTRAL
    relationship_points: int = 0
    last_interaction: str = ""
    traits: List[str] = field(default_factory=list)
    
    def update_relationship(self, change: int):
        """Update relationship level based on points"""
        self.relationship_points = max(-10, min(10, self.relationship_points + change))
        
        # Update relationship level based on points
        if self.relationship_points <= -7:
            self.relationship = RelationshipLevel.HOSTILE
        elif self.relationship_points <= -3:
            self.relationship = RelationshipLevel.UNFRIENDLY
        elif self.relationship_points <= 2:
            self.relationship = RelationshipLevel.NEUTRAL
        elif self.relationship_points <= 6:
            self.relationship = RelationshipLevel.FRIENDLY
        elif self.relationship_points <= 9:
            self.relationship = RelationshipLevel.TRUSTED
        else:
            self.relationship = RelationshipLevel.ALLY

class WorldState:
    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.locations = ["Village Square", "Dark Forest", "Mystic Caverns", "Abandoned Tower"]
        self.current_location = "Village Square"
        self.time_of_day = "morning"
        self.quests = {}
        
    def add_character(self, name: str, description: str, traits: List[str] = None):
        if name not in self.characters:
            self.characters[name] = Character(
                name=name,
                description=description,
                traits=traits or []
            )
    
    def get_character(self, name: str) -> Optional[Character]:
        return self.characters.get(name)
    
    def update_character_relationship(self, name: str, change: int):
        if name in self.characters:
            self.characters[name].update_relationship(change)
    
    def to_dict(self):
        return {
            "characters": {name: {
                "relationship": char.relationship.name,
                "relationship_points": char.relationship_points,
                "last_interaction": char.last_interaction,
                "traits": char.traits
            } for name, char in self.characters.items()},
            "current_location": self.current_location,
            "time_of_day": self.time_of_day
        }

# Custom CSS for better styling
st.markdown("""
    <style>
    .story-container {
        background-color: #2d2d2d;
        color: #f0f0f0;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        max-height: 400px;
        overflow-y: auto;
        font-family: 'Georgia', serif;
        line-height: 1.6;
    }
    .choice-btn {
        margin: 5px;
        min-width: 200px;
    }
    .header {
        color: #4CAF50;
    }
    .user-choice {
        color: #64B5F6;
        font-style: italic;
    }
    .narrative-event {
        color: #FFA000;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Configuration for local Llama 3.1 model
LOCAL_MODEL_URL = "http://127.0.0.1:1234/v1/chat/completions"

def query_local_model(prompt: str, system_prompt: str = None) -> str:
    """Query the local LLM with the given prompt and optional system message."""
    headers = {
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": "local-model",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(LOCAL_MODEL_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error querying local model: {str(e)}"


def generate_suggested_actions(story_context: str) -> List[str]:
    """Generate suggested actions based on the current story context."""
    system_prompt = """You are an AI that suggests 3-4 possible actions a player could take next in a text-based adventure game. 
    Keep each suggestion short (2-5 words) and action-oriented. Return them as a JSON array of strings."""
    
    prompt = f"""Based on this story context, suggest 3-4 possible actions the player could take next. 
    Return ONLY a JSON array of strings, nothing else.
    
    Story context: {story_context}
    
    Example response: ["Look around the room", "Talk to the stranger", "Open the chest", "Leave the area"]
    """
    
    try:
        response = query_local_model(prompt, system_prompt)
        # Extract JSON array from the response
        start = response.find('[')
        end = response.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = response[start:end]
            return json.loads(json_str)
    except Exception as e:
        print(f"Error generating suggestions: {e}")
    
    # Default suggestions if generation fails
    return ["Look around", "Search the area", "Continue forward"]

def get_arc_hint(arc_progress: int) -> str:
    """Get narrative arc hint based on progress."""
    if arc_progress < 3:
        return "The world feels calm, but something bigger is stirring."
    elif arc_progress < 6:
        return "You sense unseen forces nudging you toward a hidden truth."
    else:
        return "The climax draws near, every choice feels heavy with consequence."

# Initialize session state
if "story" not in st.session_state:
    st.session_state.story = "You awaken in a quiet village at dawn..."
    st.session_state.choices = []
    st.session_state.arc_progress = 0
    st.session_state.suggested_actions = []
    st.session_state.last_choice = ""
    st.session_state.last_twist = ""
    st.session_state.is_loading = False
    
    # Initialize world state
    st.session_state.world = WorldState()
    
    # Add some initial characters
    st.session_state.world.add_character(
        "Old Man Jenkins",
        "An elderly villager with a long white beard and kind eyes.",
        ["wise", "friendly", "knowledgeable"]
    )
    st.session_state.world.add_character(
        "Captain Rourke",
        "The grizzled captain of the village guard, always on the lookout for trouble.",
        ["brave", "suspicious", "dutiful"]
    )
    st.session_state.world.add_character(
        "Mysterious Stranger",
        "A hooded figure who watches from the shadows.",
        ["mysterious", "elusive", "dangerous"]
    )
    
    # Initialize character relationships
    st.session_state.world.update_character_relationship("Old Man Jenkins", 2)  # Starts friendly
    st.session_state.world.update_character_relationship("Captain Rourke", -1)  # Slightly unfriendly
    st.session_state.world.update_character_relationship("Mysterious Stranger", -3)  # Unfriendly

# Page setup
st.set_page_config(
    page_title="Living Pages", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar with character and world info
with st.sidebar:
    st.header("📊 Story Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Choices Made", len(st.session_state.choices))
    with col2:
        st.metric("Arc Progress", f"{min(100, st.session_state.arc_progress * 10)}%")
    
    # Character relationships
    st.markdown("---")
    st.header("👥 Characters")
    
    # Show all characters, but indicate if they haven't been met yet
    all_chars = list(st.session_state.world.characters.values())
    
    if not all_chars:
        st.info("No characters have been added to the story yet.")
    else:
        for char in all_chars:
            # Get relationship color
            rel_color = {
                RelationshipLevel.HOSTILE: "#ff4b4b",
                RelationshipLevel.UNFRIENDLY: "#ff8c8c",
                RelationshipLevel.NEUTRAL: "#f0f0f0",
                RelationshipLevel.FRIENDLY: "#90EE90",
                RelationshipLevel.TRUSTED: "#4CAF50",
                RelationshipLevel.ALLY: "#2E7D32"
            }.get(char.relationship, "#f0f0f0")
            
            # Check if character has been mentioned in the story
            has_been_mentioned = char.name.lower() in st.session_state.story.lower()
            
            # Show a different icon based on relationship status
            rel_icon = {
                RelationshipLevel.HOSTILE: "👿",
                RelationshipLevel.UNFRIENDLY: "😠",
                RelationshipLevel.NEUTRAL: "😐",
                RelationshipLevel.FRIENDLY: "🙂",
                RelationshipLevel.TRUSTED: "😊",
                RelationshipLevel.ALLY: "🤝"
            }.get(char.relationship, "❓")
            
            with st.expander(f"{rel_icon} {char.name} - {char.relationship.name}" + ("" if has_been_mentioned else " (Not yet met)")):
                st.write(char.description)
                st.progress((char.relationship_points + 10) / 20, 
                          f"Relationship: {char.relationship.name} ({char.relationship_points})")
                
                # Show traits as tags
                if char.traits:
                    cols = st.columns(3)
                    for i, trait in enumerate(char.traits):
                        cols[i % 3].markdown(f"`{trait}`")
    
    # World state
    st.markdown("---")
    st.header("🌍 World")
    st.markdown(f"**Location:** {st.session_state.world.current_location}")
    st.markdown(f"**Time of Day:** {st.session_state.world.time_of_day.title()}")
    
    # Debug info (collapsed by default)
    with st.expander("🔧 Debug Info", expanded=False):
        st.json(st.session_state.world.to_dict())
        
        # Add a text area for the full story with a proper label
        st.write("### Full Story")
        st.text_area("story_debug", value=st.session_state.story, height=200, label_visibility="collapsed")

# Main content
st.title("📖 Living Pages: A Dynamic Narrative System")

# Story display
with st.container():
    st.markdown(f'<div class="story-container">{st.session_state.story}</div>', unsafe_allow_html=True)

# Generate suggested actions if none exist
if not st.session_state.suggested_actions:
    with st.spinner("Generating possible actions..."):
        st.session_state.suggested_actions = generate_suggested_actions(st.session_state.story)

# Display suggested actions as buttons
st.subheader("What will you do next?")

# Create columns for the action buttons
cols = st.columns(2)
for i, action in enumerate(st.session_state.choices[-4:] + st.session_state.suggested_actions):
    if i < 4:  # Only show up to 4 buttons
        with cols[i % 2]:
            if st.button(action, key=f"action_{i}", use_container_width=True):
                st.session_state.last_choice = action
                st.session_state.is_loading = True
                st.rerun()

# Custom action input
with st.expander("Or type your own action"):
    custom_action = st.text_input("Your action:", key="custom_action")
    if st.button("Submit Custom Action"):
        if custom_action.strip():
            st.session_state.last_choice = custom_action
            st.session_state.is_loading = True
            st.rerun()

# Process the selected action
if st.session_state.is_loading and st.session_state.last_choice:
    with st.spinner("Continuing the story..."):
        # Update story state
        user_choice = st.session_state.last_choice
        st.session_state.choices.append(user_choice)
        st.session_state.arc_progress += 1

        # Generate a twist or character interaction based on the story context
        twist = ""
        if random.random() < 0.4:  # 40% chance of a narrative event
            if random.random() < 0.6:  # 60% chance of a character interaction
                # Get mentioned characters in the story
                mentioned_chars = [char for char in st.session_state.world.characters.values() 
                                 if char.name.lower() in st.session_state.story.lower()]
                
                if mentioned_chars:
                    # Choose a random character to interact with
                    char = random.choice(mentioned_chars)
                    
                    # Determine interaction type based on relationship
                    if char.relationship in [RelationshipLevel.HOSTILE, RelationshipLevel.UNFRIENDLY]:
                        interaction_type = random.choice(["challenge", "threat", "warning"])
                    elif char.relationship == RelationshipLevel.NEUTRAL:
                        interaction_type = random.choice(["observe", "question", "comment"])
                    else:
                        interaction_type = random.choice(["help", "advice", "gift"])
                    
                    # Generate the interaction
                    twist_prompt = f"""
                    Current story: {st.session_state.story}
                    
                    Character: {char.name}
                    Character traits: {', '.join(char.traits)}
                    Relationship: {char.relationship.name}
                    
                    Generate a short interaction where {char.name} {interaction_type}s the player in 1-2 sentences.
                    Example: "Old Man Jenkins warns you about the dangers of the forest at night."
                    """
                    twist = query_local_model(twist_prompt, "You are a creative writer who creates engaging character interactions.")
                    
                    # Update relationship based on interaction
                    if interaction_type in ["help", "advice", "gift"]:
                        st.session_state.world.update_character_relationship(char.name, 1)
                    elif interaction_type in ["threat", "challenge"]:
                        st.session_state.world.update_character_relationship(char.name, -1)
                    
                    # Update last interaction time
                    char.last_interaction = "Just now"
            else:  # 40% chance of a regular twist
                twist_prompt = f"""The current story: {st.session_state.story}
                
                The player chose to: {user_choice}
                
                Generate a short, surprising narrative twist (1-2 sentences). Keep it engaging and relevant.
                Example: 'As you reach for the door, you hear a loud crash from the room above.'
                """
                twist = query_local_model(twist_prompt, "You are a creative writing assistant that adds exciting twists to stories.")
                
                # Small chance to discover a new character
                if random.random() < 0.2:  # 20% chance when a twist occurs
                    new_char_name = query_local_model(
                        "Generate a fantasy character name (just the name, no quotes or punctuation)",
                        "You are a creative writer who invents interesting character names."
                    ).strip('"\'')
                    
                    if new_char_name and new_char_name not in st.session_state.world.characters:
                        char_traits = random.sample(
                            ["mysterious", "friendly", "suspicious", "wise", "playful", "serious", "eccentric"],
                            k=random.randint(2, 4)
                        )
                        st.session_state.world.add_character(
                            new_char_name,
                            f"A {char_traits[0]} figure you've just encountered.",
                            char_traits
                        )
                        twist += f"\n\nYou notice {new_char_name} watching you from a distance..."
            
            st.session_state.last_twist = twist

        # Get arc guidance
        arc_hint = get_arc_hint(st.session_state.arc_progress)

        # Generate story continuation

        # Generate story continuation
        system_prompt = """You are a master storyteller. Continue the narrative in an engaging way that:
        1. Acknowledges the player's last action
        2. Incorporates any narrative twists naturally
        3. Advances the story in a coherent way
        4. Leaves room for interesting future developments
        Keep it concise (2-4 paragraphs)."""
        
        # Create the prompt with proper string escaping
        twist_section = f'NARRATIVE TWIST (if any):\n{twist}\n\n' if twist else ''
        prompt = f"""Continue the story based on this context:
        
CURRENT STORY:
{st.session_state.story}

PLAYER'S ACTION:
{user_choice}

{twist_section}NARRATIVE ARC HINT:
{arc_hint}

Continue the story in a way that's engaging and maintains player agency. Don't describe the player's actions for them - just describe what happens as a result."""
        
        continuation = query_local_model(prompt, system_prompt)
        
        # Format the update
        update_text = f"\n\n> **{user_choice}**"
        if twist:
            update_text += f"\n\n*{twist}*\n"
        update_text += f"\n{continuation}"
        
        # Update the story
        st.session_state.story += update_text
        
        # Reset for next interaction
        st.session_state.suggested_actions = []
        st.session_state.is_loading = False
        st.session_state.last_choice = ""
        st.rerun()

# Add some spacing at the bottom
st.markdown("<br><br>", unsafe_allow_html=True)

# Debug info (collapsed by default)
with st.expander("📝 Story Log", expanded=False):
    st.write("### Story So Far")
    st.text_area("", st.session_state.story, height=200)
    
    st.write("### Your Choices")
    for i, choice in enumerate(st.session_state.choices, 1):
        st.write(f"{i}. {choice}")
    
    if st.button("Start New Game"):
        st.session_state.clear()
        st.rerun()
